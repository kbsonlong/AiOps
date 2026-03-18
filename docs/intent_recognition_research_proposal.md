# Qwen3.5:2B 意图识别增强调研方案

**文档版本**: v1.0
**创建日期**: 2026-03-18
**最后更新**: 2026-03-18
**负责人**: 待定
**评审状态**: ⏳ 待评审

### 变更记录

- **v1.0** (2026-03-18): 初始版本，定义调研方案和实施计划

---

## 1. 调研背景

### 1.1 项目现状

AIOps 项目当前使用 **qwen3.5:2b** 模型作为路由器进行意图识别，通过 `classify_query()` 函数实现用户查询的分类：

```python
# 当前架构
用户查询
    ↓
qwen3.5:2b (意图识别 + 分类)
    ↓
路由到 5 个专业代理 (metrics/logs/fault/security/knowledge_base)
    ↓
结果汇总
```

**当前配置**：
```bash
ROUTER_LLM_MODEL=qwen3.5:2b     # 路由模型
ROUTER_TIMEOUT=15                # 超时 15 秒
ROUTER_MAX_TOKENS=512            # 最大 512 tokens
ROUTER_TEMPERATURE=0             # 确定性输出
```

**已实现的统计追踪**：
- LLM 调用次数 / 成功率 / 平均延迟
- Fallback 触发次数
- 分类源分布 / 严重程度分布
- 详细分类记录（最近 100 条）

### 1.2 问题定义

根据对项目的分析，当前意图识别系统存在以下潜在问题：

| 问题类别 | 问题描述 | 影响程度 |
|---------|---------|---------|
| **准确率未知** | 缺乏定量评估，无法准确判断分类准确率 | 🟡 中 |
| **无数据集** | 没有标注的意图识别测试/训练数据集 | 🔴 高 |
| **优化困难** | 无法系统化地改进提示词或模型参数 | 🟡 中 |
| **扩展受限** | 添加新意图类别需要大量人工调优 | 🟡 中 |
| **泛化能力** | 对未见过的问题泛化能力未知 | 🟡 中 |

### 1.3 调研目标

**主要目标**：
1. ✅ 建立意图识别评估基准（测试集 + 评估指标）
2. ✅ 对比不同优化方案的效果
3. ✅ 提供可操作的实施建议

**次要目标**：
1. 评估是否需要进行模型微调
2. 探索自动化优化（如 AutoResearch）的可行性
3. 建立持续改进机制

---

## 2. 技术方案对比

### 2.1 方案概览

| 方案 | 技术路径 | 工作量 | 预期效果 | 风险 |
|-----|---------|-------|---------|------|
| **A: 提示词工程** | 优化系统提示词 + few-shot | 低 | 提升 5-15% | 低 |
| **B: LLaMA-Factory 微调** | LoRA 微调 qwen3.5:2b | 中 | 提升 15-30% | 中 |
| **C: 自主研究代理** | AutoResearch 自动优化 | 高 | 未知 | 高 |
| **D: 数据驱动** | 从统计生成训练数据 | 低-中 | 提升 10-20% | 低 |

### 2.2 详细方案分析

#### 方案 A: 提示词工程

**技术路线**：
1. 分析当前提示词的不足
2. 添加 few-shot 示例
3. 优化输出格式约束
4. A/B 测试验证效果

**示例改进**：
```python
# 当前提示词（简化）
"你是一个 AIOps 系统的智能路由分类器..."
"将查询分类到合适的专业代理..."

# 改进后
"你是 AIOps 系统的智能路由分类器。你的任务是分析用户查询并分类。

## 分类规则
1. **metrics**: 包含具体指标名称 (cpu/memory/disk/network) 或数值查询
2. **logs**: 包含 log/error/exception/warning 等日志关键词
3. **fault**: 包含诊断/根因/异常/崩溃等故障关键词
4. **security**: 包含安全/漏洞/入侵/权限等安全关键词
5. **knowledge_base**: 其他通用知识查询

## Few-shot 示例
Q: 'CPU 使用率很高，怎么办？'
A: {\"source\": \"metrics\", \"severity\": \"medium\"}

Q: '查看昨天的错误日志'
A: {\"source\": \"logs\", \"severity\": \"low\"}

Q: '帮我分析一下系统为什么崩溃了'
A: {\"source\": \"fault\", \"severity\": \"high\"}

现在请分类以下查询..."
```

**优势**：
- ✅ 无需额外资源
- ✅ 可快速迭代
- ✅ 风险低

**劣势**：
- ❌ 效果提升有限
- ❌ 依赖模型原有能力

#### 方案 B: LLaMA-Factory 微调

**技术路线**：
1. 准备标注数据集（至少 500 条）
2. 使用 LLaMA-Factory 配置 LoRA 微调
3. 在验证集上评估效果
4. 部署最优模型

**配置示例**：
```yaml
# config/llamafactory_intent.yaml
model_name_or_path: Qwen/Qwen2.5-0.5B
task: intent_classification
num_labels: 20  # 5 sources × 4 severities

lora:
  r: 16
  alpha: 32
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]

training:
  num_train_epochs: 3
  per_device_train_batch_size: 8
  learning_rate: 2e-4
  warmup_ratio: 0.1
```

**优势**：
- ✅ 效果提升明显
- ✅ 模型专门化
- ✅ 社区支持好

**劣势**：
- ❌ 需要标注数据
- ❌ 训练时间较长
- ❌ 需要硬件资源

#### 方案 C: 自主研究代理

**技术路线**：
1. 基于 autoresearch 理念改造
2. 定义搜索空间（LoRA 参数、学习率等）
3. 自动运行实验并评估
4. 选择最优配置

**架构设计**：
```
AutoResearch Agent
    ↓
搜索空间定义
    ├─ LoRA r: [8, 16, 32]
    ├─ Learning rate: [1e-5, 2e-5, 5e-5]
    ├─ Batch size: [4, 8, 16]
    └─ Epochs: [3, 5, 10]
    ↓
实验循环 (每次 30min)
    ├─ 修改配置
    ├─ 训练模型
    ├─ 评估效果
    └─ 保留/丢弃
    ↓
收敛到最优配置
```

**优势**：
- ✅ 自动化探索
- ✅ 可发现非直观组合
- ✅ 研究价值高

**劣势**：
- ❌ 开发工作量大
- ❌ 计算资源消耗大
- ❌ 不确定性高

#### 方案 D: 数据驱动

**技术路线**：
1. 从 `classification_metrics` 收集真实查询
2. 人工标注或自动标注
3. 生成训练/验证数据集
4. 评估当前模型基线

**数据收集脚本**：
```python
# scripts/collect_intent_data.py
from aiops.core.classification_metrics import get_metrics

def collect_training_data():
    metrics = get_metrics()
    records = metrics.get_recent_records(limit=1000)

    high_quality = []
    medium_quality = []

    for record in records:
        data = {
            "query": record.query,
            "timestamp": record.timestamp,
        }

        if record.method == "llm" and record.llm_latency_ms < 1000:
            # 高质量样本：LLM 快速成功分类
            data["label"] = f"{record.source}_{record.severity}"
            data["confidence"] = "high"
            high_quality.append(data)
        elif record.method == "fallback":
            # 中等质量样本：需要人工验证
            data["suggested_label"] = f"{record.source}_{record.severity}"
            data["confidence"] = "medium"
            medium_quality.append(data)

    return {
        "high_quality": high_quality,
        "medium_quality": medium_quality,
        "stats": {
            "total": len(records),
            "high_confidence": len(high_quality),
            "needs_review": len(medium_quality)
        }
    }
```

**优势**：
- ✅ 基于真实数据
- ✅ 可持续改进
- ✅ 风险低

**劣势**：
- ❌ 需要数据积累
- ❌ 可能需要人工标注

---

## 3. 调研计划

### 3.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────┐
│                    调研项目时间线 (4 周)                          │
├─────────────────────────────────────────────────────────────────┤
│  Week 1          Week 2          Week 3          Week 4         │
│  ┌─────┐         ┌─────┐         ┌─────┐         ┌─────┐        │
│  │ 基准 │   →     │ 实验 │   →     │ 评估 │   →     │ 决策 │        │
│  │ 建立 │         │ 执行 │         │ 分析 │         │ 建议 │        │
│  └─────┘         └─────┘         └─────┘         └─────┘        │
│    ↓               ↓               ↓               ↓            │
│  数据集          方案A/B          效果对比          最终          │
│  构建           初步实验          深度分析          报告          │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 详细任务分解

#### Week 1: 基准建立

| 任务 | 负责人 | 工作量 | 交付物 |
|-----|-------|-------|-------|
| 1.1 数据收集脚本开发 | - | 4h | `scripts/collect_intent_data.py` |
| 1.2 测试集标注 | - | 8h | `data/intent_test.jsonl` (200条) |
| 1.3 评估框架实现 | - | 4h | `tests/intent_evaluation.py` |
| 1.4 基线测试 | - | 2h | 当前模型准确率报告 |

**数据标注规范**：
```json
{
  "query": "CPU 使用率很高，怎么办？",
  "source": "metrics",
  "severity": "medium",
  "intent": "operation",
  "language": "zh",
  "difficulty": "easy",
  "notes": "明确的指标查询"
}
```

#### Week 2: 实验执行

| 任务 | 负责人 | 工作量 | 交付物 |
|-----|-------|-------|-------|
| 2.1 提示词优化 (方案A) | - | 6h | 优化后的提示词版本 |
| 2.2 Few-shot 示例收集 | - | 4h | 20 个高质量示例 |
| 2.3 LLaMA-Factory 配置 | - | 6h | 微调配置文件 |
| 2.4 数据集准备 (如需微调) | - | 8h | 训练/验证集 |

#### Week 3: 评估分析

| 任务 | 负责人 | 工作量 | 交付物 |
|-----|-------|-------|-------|
| 3.1 方案 A 效果评估 | - | 4h | 准确率提升报告 |
| 3.2 方案 B 效果评估 | - | 6h | 微调模型对比 |
| 3.3 错误分析 | - | 6h | 错误分类模式报告 |
| 3.4 消融实验 | - | 4h | 各组件贡献度 |

#### Week 4: 决策建议

| 任务 | 负责人 | 工作量 | 交付物 |
|-----|-------|-------|-------|
| 4.1 综合效果对比 | - | 4h | 方案对比矩阵 |
| 4.2 ROI 分析 | - | 4h | 成本效益分析 |
| 4.3 风险评估 | - | 3h | 实施风险评估 |
| 4.4 最终建议报告 | - | 5h | 本文档更新 |

---

## 4. 评估指标

### 4.1 核心指标

| 指标 | 计算方式 | 目标值 | 说明 |
|-----|---------|-------|------|
| **Accuracy** | 正确分类数 / 总数 | >90% | 整体准确率 |
| **F1-score (macro)** | 各类别 F1 的平均值 | >0.85 | 类别平衡指标 |
| **Precision@1** | Top-1 预测准确率 | >90% | 最重要指标 |
| **Recall@High** | 高严重度召回率 | >95% | 关键问题不漏报 |
| **Avg Latency** | 平均响应时间 | <500ms | 用户体验 |
| **Fallback Rate** | 降级率 | <5% | 稳定性 |

### 4.2 辅助指标

| 指标 | 说明 | 用途 |
|-----|------|------|
| **Per-class Accuracy** | 各类别准确率 | 发现弱项 |
| **Confusion Matrix** | 混淆矩阵 | 分析错误模式 |
| **Calibration Error** | 预测置信度校准 | 可信度评估 |
| **Inference Speed** | tokens/sec | 性能基准 |

### 4.3 评估代码框架

```python
# tests/intent_evaluation.py
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)
import json

class IntentEvaluator:
    """意图识别评估器"""

    def __init__(self, test_data_path: str):
        self.test_data = self._load_test_data(test_data_path)

    def evaluate(self, predictions, labels):
        """计算所有评估指标"""
        return {
            "accuracy": accuracy_score(labels, predictions),
            "f1_macro": f1_score(labels, predictions, average="macro"),
            "f1_micro": f1_score(labels, predictions, average="micro"),
            "classification_report": classification_report(
                labels, predictions,
                target_names=self._get_label_names()
            ),
            "confusion_matrix": confusion_matrix(labels, predictions),
        }

    def per_class_accuracy(self, predictions, labels):
        """计算各类别准确率"""
        report = classification_report(
            labels, predictions,
            target_names=self._get_label_names(),
            output_dict=True
        )
        return {name: report[name]["precision"]
                for name in self._get_label_names()}
```

---

## 5. 风险评估

### 5.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|------|------|---------|
| 数据集不足 | 🟡 中 | 🔴 高 | 使用数据增强、迁移学习 |
| 微调不收敛 | 🟡 中 | 🟡 中 | 调整超参、使用 LoRA |
| 效果不理想 | 🟡 中 | 🟡 中 | 多方案对比、降级到提示词工程 |
| 资源不足 | 🟢 低 | 🟡 中 | 优先级排序、云资源 |

### 5.2 项目风险

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|------|------|---------|
| 时间延误 | 🟡 中 | 🟡 中 | 分阶段交付、MVP 优先 |
| 人力不足 | 🟡 中 | 🔴 高 | 外包部分任务、调整范围 |
| 目标变更 | 🟢 低 | 🟡 中 | 敏捷调整、保持沟通 |

---

## 6. 成功标准

### 6.1 最小可行产品 (MVP)

**必须达成**：
- ✅ 建立至少 200 条标注测试集
- ✅ 获得当前模型基线准确率
- ✅ 至少尝试一种优化方案
- ✅ 产出量化对比报告

### 6.2 理想目标

**期望达成**：
- 🎯 意图识别准确率提升 >10%
- 🎯 Fallback 率降低 >50%
- 🎯 平均延迟保持或降低
- 🎯 建立持续改进机制

### 6.3 降级方案

如果遇到无法克服的障碍，降级到：
- 仅完成提示词优化
- 输出分析报告，不实施微调
- 建议后续调研方向

---

## 7. 资源需求

### 7.1 人力需求

| 角色 | 工作量 | 说明 |
|-----|-------|------|
| 算法工程师 | 40h | 方案设计、实验执行 |
| 数据标注员 | 20h | 数据集标注 |
| 评审专家 | 4h | 方案评审、建议 |

### 7.2 计算资源

| 资源 | 配置 | 用途 | 时长 |
|-----|------|------|------|
| Mac M1/M2/M3 | 16GB+ RAM | 模型推理/评估 | 持续 |
| GPU (可选) | A100/V100 | 模型微调 | 10-20h |
| 云存储 | 100GB | 数据/模型存储 | 持续 |

### 7.3 数据需求

| 数据类型 | 数量 | 来源 | 质量要求 |
|---------|------|------|---------|
| 测试集 | 200-500 条 | 人工标注 | 高质量 |
| 训练集 (可选) | 500-1000 条 | 收集+标注 | 高质量 |
| Few-shot 示例 | 20-50 条 | 人工精选 | 典型案例 |

---

## 8. 交付物清单

### 8.1 文档交付

- [ ] 调研方案（本文档）
- [ ] 数据集说明文档
- [ ] 评估报告
- [ ] 实施建议报告

### 8.2 代码交付

- [ ] `scripts/collect_intent_data.py` - 数据收集脚本
- [ ] `tests/intent_evaluation.py` - 评估框架
- [ ] `scripts/evaluate_intent.py` - 意图评估工具
- [ ] 配置文件（如需微调）

### 8.3 数据交付

- [ ] `data/intent_test.jsonl` - 测试集
- [ ] `data/intent_train.jsonl` - 训练集（可选）
- [ ] `data/few_shot_examples.json` - Few-shot 示例
- [ ] `data/evaluation_results.json` - 评估结果

---

## 9. 评审检查清单

### 9.1 方案评审

在开始执行前，请确认：

- [ ] **目标明确**: 调研目标与业务目标一致
- [ ] **方案可行**: 技术方案经过充分论证
- [ ] **资源充足**: 人力和计算资源已落实
- [ ] **时间合理**: 4 周时间线可接受
- [ ] **风险可控**: 主要风险有缓解措施

### 9.2 中期检查

Week 2 结束时检查：

- [ ] 数据集已准备就绪
- [ ] 基线测试已完成
- [ ] 至少一个方案已开始实验
- [ ] 无阻碍性问题

### 9.3 最终验收

项目结束时检查：

- [ ] 所有交付物已完成
- [ ] 效果对比清晰可验证
- [ ] 建议报告可操作
- [ ] 代码和数据已归档

---

## 10. 下一步行动

### 10.1 立即行动 (评审通过后)

1. **确认资源**: 分配人力和计算资源
2. **建立环境**: 配置开发环境和依赖
3. **开始数据收集**: 运行数据收集脚本

### 10.2 启动命令

```bash
# 1. 确认环境
uv sync

# 2. 收集现有数据
python -m scripts.collect_intent_data --output data/raw_queries.json

# 3. 开始标注
python -m scripts.annotate_intents --input data/raw_queries.json

# 4. 运行基线测试
python -m tests.intent_evaluation --baseline
```

---

## 附录

### A. 参考资源

- [LLaMA-Factory 文档](https://github.com/hiyouga/LLaMA-Factory)
- [autoresearch-macos](https://github.com/miolini/autoresearch-macos)
- [Qwen2.5 模型家族](https://huggingface.co/Qwen)
- [CLINC OOS 数据集](https://github.com/clinc/oos)

### B. 联系方式

**项目负责人**: 待定
**技术顾问**: Claude Code
**评审周期**: 每周一次

---

**文档状态**: ⏳ 等待评审

**评审意见**:
<!--
请在此处添加评审意见：
1. 方案是否可行？
2. 时间和资源是否充足？
3. 是否有遗漏的重要考虑？
-->
