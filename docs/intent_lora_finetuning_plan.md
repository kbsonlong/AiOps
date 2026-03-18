# 意图识别 LoRA 微调实施方案

**文档版本**: v1.0
**创建日期**: 2026-03-18
**负责人**: 待定
**评审状态**: ⏳ 待评审

---

## 1. 项目概述

### 1.1 背景与目标

AIOps 项目当前使用 **qwen2.5:3b** 模型进行意图识别，通过 `classify_query()` 函数将用户查询分类到 5 个专业代理：

- **metrics**: 系统指标查询
- **logs**: 日志分析
- **fault**: 故障诊断
- **security**: 安全检查
- **knowledge_base**: 通用知识

**当前问题**：
- 缺乏定量评估基准
- 分类准确率未知
- 优化依赖手工调参

**项目目标**：
1. 建立意图识别评估基准（测试集 + 评估指标）
2. 通过 LoRA 微调提升分类准确率 **>10%**
3. 实现自动化参数搜索（替代手工调参）
4. 降低 Fallback 率 **>50%**

### 1.2 技术选型

| 组件 | 选型 | 理由 |
|------|------|------|
| **微调框架** | LLaMA-Factory | 成熟稳定、支持 LoRA、社区活跃 |
| **基础模型** | qwen2.5:3b (Ollama) | 与生产环境一致 |
| **自动搜索** | 自研 AutoSearch | 轻量级、可控性强 |
| **评估指标** | Accuracy/F1/Recall | 分类任务标准指标 |
| **硬件平台** | Mac M1/M2/M3 (MPS) | 本地开发环境 |

### 1.3 扩展性需求

系统未来可能需要支持更多 Agent 类型，如：

| 潜在 Agent | 用途 | 优先级 |
|-----------|------|--------|
| **cost** | 成本分析与优化 | P2 |
| **performance** | 性能调优与建议 | P2 |
| **backup** | 备份与恢复管理 | P3 |
| **deployment** | 部署与发布管理 | P3 |
| **compliance** | 合规性检查 | P3 |

**扩展性设计原则**：
1. **配置驱动**: Agent 定义通过配置文件管理，无需修改代码
2. **模型热更新**: 支持新增类别而不破坏现有模型
3. **向后兼容**: 新 Agent 不影响现有分类
4. **渐进式迁移**: 支持从旧模型平滑迁移到新模型

---

## 2. 技术方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        意图识别 LoRA 微调系统                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  数据准备模块  │ →  │  自动搜索模块  │ →  │  评估分析模块  │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         ↓                    ↓                    ↓             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  收集真实查询  │    │  LoRA参数搜索  │    │  准确率/F1    │       │
│  │  人工标注标签  │    │  训练/验证    │    │  混淆矩阵     │       │
│  │  数据集分割   │    │  保留最优结果  │    │  错误分析     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
              ┌───────────────────────┐
              │   输出: 最优 LoRA 模型  │
              │   + 配置参数文档       │
              └───────────────────────┘
```

### 2.2 数据流设计

```
真实查询 (classification_metrics)
         ↓
    数据清洗与去重
         ↓
    人工标注 (source, severity)
         ↓
    训练集 / 验证集 / 测试集 (7:2:1)
         ↓
    LLaMA-Factory 训练
         ↓
    模型评估与选择
```

### 2.3 搜索空间定义

```yaml
# config/search_space.yaml
lora:
  r: [8, 16, 32, 64]
  alpha: [16, 32, 64, 128]
  dropout: [0.0, 0.05, 0.1]
  target_modules:
    - ["q_proj", "v_proj"]
    - ["q_proj", "v_proj", "k_proj", "o_proj"]
    - ["all-linear"]

training:
  learning_rate: [1e-5, 2e-5, 5e-5, 1e-4]
  batch_size: [4, 8, 16]
  num_epochs: [3, 5, 10]
  warmup_ratio: [0.0, 0.1, 0.2]

search:
  time_budget_minutes: 30  # 每次实验时间预算
  max_iterations: 10        # 最大搜索迭代
  strategy: random          # random / grid / bayesian
```

### 2.4 扩展性架构设计

#### 2.4.1 Agent 注册机制

```python
# aiops/core/agent_registry.py
"""
Agent 注册中心，支持动态添加新的 Agent 类型。
"""
from typing import Literal, TypedDict
from dataclasses import dataclass

class AgentDefinition(TypedDict):
    """Agent 定义"""
    name: str                    # Agent 名称
    description: str             # 功能描述
    keywords: list[str]          # 关键词列表（用于 fallback）
    severity_levels: list[str]   # 支持的严重级别
    priority: int                # 优先级（用于路由冲突）

# 当前支持的 Agent
CURRENT_AGENTS: dict[str, AgentDefinition] = {
    "metrics": {
        "name": "metrics",
        "description": "系统指标查询与监控",
        "keywords": ["cpu", "memory", "disk", "network", "指标", "监控"],
        "severity_levels": ["low", "medium", "high", "critical"],
        "priority": 1,
    },
    "logs": {
        "name": "logs",
        "description": "日志分析与查询",
        "keywords": ["log", "error", "exception", "warning", "日志"],
        "severity_levels": ["low", "medium", "high", "critical"],
        "priority": 2,
    },
    "fault": {
        "name": "fault",
        "description": "故障诊断与根因分析",
        "keywords": ["诊断", "根因", "异常", "崩溃", "故障"],
        "severity_levels": ["low", "medium", "high", "critical"],
        "priority": 3,
    },
    "security": {
        "name": "security",
        "description": "安全检查与漏洞扫描",
        "keywords": ["安全", "漏洞", "入侵", "权限", "攻击"],
        "severity_levels": ["low", "medium", "high", "critical"],
        "priority": 4,
    },
    "knowledge_base": {
        "name": "knowledge_base",
        "description": "通用知识查询",
        "keywords": [],
        "severity_levels": ["low", "medium", "high", "critical"],
        "priority": 5,  # 默认兜底
    },
}

class AgentRegistry:
    """Agent 注册中心"""

    def __init__(self):
        self._agents = CURRENT_AGENTS.copy()

    def register_agent(self, agent_def: AgentDefinition) -> None:
        """注册新的 Agent 类型"""
        name = agent_def["name"]
        if name in self._agents:
            raise ValueError(f"Agent '{name}' already exists")
        self._agents[name] = agent_def

    def unregister_agent(self, name: str) -> None:
        """注销 Agent 类型（慎用）"""
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found")
        del self._agents[name]

    def get_agent(self, name: str) -> AgentDefinition:
        """获取 Agent 定义"""
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """列出所有 Agent 名称"""
        return list(self._agents.keys())

    def get_num_labels(self) -> int:
        """获取分类标签总数（用于模型输出层）"""
        return len(self._agents) * 4  # 假设每个 Agent 有 4 个 severity

# 全局单例
_registry = AgentRegistry()

def get_registry() -> AgentRegistry:
    """获取 Agent 注册中心实例"""
    return _registry
```

#### 2.4.2 配置驱动的 Agent 定义

```yaml
# config/agents.yaml
# Agent 类型配置文件，支持热更新

agents:
  metrics:
    name: metrics
    display_name: "指标监控"
    description: "CPU、内存、磁盘、网络等系统指标查询"
    enabled: true
    keywords:
      - cpu
      - memory
      - disk
      - network
      - 指标
      - 监控
      - 使用率
    severity_levels: [low, medium, high, critical]
    priority: 1
    examples:
      - "CPU 使用率很高"
      - "查看内存占用"
      - "磁盘空间不足"

  logs:
    name: logs
    display_name: "日志分析"
    description: "错误日志、异常堆栈、警告信息查询"
    enabled: true
    keywords:
      - log
      - error
      - exception
      - warning
      - 日志
      - 错误
    severity_levels: [low, medium, high, critical]
    priority: 2
    examples:
      - "查看错误日志"
      - "有哪些异常"
      - "最近的 warning"

  fault:
    name: fault
    display_name: "故障诊断"
    description: "系统异常诊断、根因分析、故障排查"
    enabled: true
    keywords:
      - 诊断
      - 根因
      - 异常
      - 崩溃
      - 故障
    severity_levels: [low, medium, high, critical]
    priority: 3
    examples:
      - "系统为什么崩溃"
      - "帮我分析故障"
      - "找出问题原因"

  security:
    name: security
    display_name: "安全检查"
    description: "安全漏洞、入侵检测、权限审计"
    enabled: true
    keywords:
      - 安全
      - 漏洞
      - 入侵
      - 权限
      - 攻击
    severity_levels: [low, medium, high, critical]
    priority: 4
    examples:
      - "检查安全漏洞"
      - "有没有异常登录"
      - "权限配置检查"

  knowledge_base:
    name: knowledge_base
    display_name: "知识库"
    description: "通用运维知识查询"
    enabled: true
    keywords: []
    severity_levels: [low, medium, high, critical]
    priority: 99  # 兜底
    examples:
      - "如何配置监控"
      - "部署文档在哪"

# 未来可扩展的 Agent（已预留配置）
  # cost:
  #   name: cost
  #   display_name: "成本分析"
  #   description: "云资源成本分析与优化建议"
  #   enabled: false  # 暂未启用
  #   keywords: [成本, 费用, 预算, 优化]
  #   severity_levels: [low, medium, high]
  #   priority: 6
```

#### 2.4.3 模型扩展策略

**方案一：增量训练 (推荐)**

```python
# 增量添加新 Agent 而不重新训练整个模型
class IncrementalTrainingStrategy:
    """
    增量训练策略：添加新 Agent 时，保留原有模型权重。

    优势：
    - 不影响现有分类性能
    - 训练数据量小
    - 快速迭代

    步骤：
    1. 加载现有 LoRA 模型
    2. 扩展输出层 (5 → 6 个 Agent)
    3. 仅在新类别 + 部分旧数据上微调
    4. 验证旧类别性能无回退
    """

    def add_new_agent(
        self,
        existing_model_path: str,
        new_agent_name: str,
        new_training_data: list
    ):
        # 1. 加载现有模型
        base_model = load_lora_model(existing_model_path)

        # 2. 扩展分类头
        num_old_classes = base_model.num_labels
        num_new_classes = num_old_classes + 4  # 新 Agent × 4 severities
        base_model.resize_classifier(num_new_classes)

        # 3. 混合数据集
        # - 新 Agent 数据
        # - 10% 旧数据（防止遗忘）
        mixed_data = self._prepare_mixed_data(
            new_data=new_training_data,
            old_data_sample_ratio=0.1
        )

        # 4. 增量微调（较小学习率）
        trainer = LoRATrainer(
            model=base_model,
            learning_rate=1e-5,  # 更小的学习率
            num_epochs=3,
        )
        trainer.train(mixed_data)

        # 5. 验证
        self._validate_no_regression(base_model)

        return base_model
```

**方案二：多任务学习头**

```python
# 使用独立的分类头，便于扩展
class MultiHeadIntentModel:
    """
    多头模型：每个 Agent 一个独立的分类头。

    优势：
    - 添加新 Agent 不影响现有头
    - 可以独立训练/更新
    - 便于 A/B 测试

    架构：
                    Shared Backbone
                    (qwen2.5:3b + LoRA)
                          ↓
        ┌─────────┬─────────┬─────────┬─────────┐
        ↓         ↓         ↓         ↓         ↓
    metrics    logs     fault   security  knowledge
      Head      Head     Head      Head      Head
    """

    def __init__(self, base_model):
        self.backbone = base_model
        self.heads = nn.ModuleDict({
            "metrics": ClassificationHead(num_classes=4),
            "logs": ClassificationHead(num_classes=4),
            "fault": ClassificationHead(num_classes=4),
            "security": ClassificationHead(num_classes=4),
            "knowledge_base": ClassificationHead(num_classes=4),
        })

    def add_agent(self, agent_name: str):
        """添加新 Agent 分类头"""
        self.heads[agent_name] = ClassificationHead(num_classes=4)

    def forward(self, input_ids, attention_mask, agent_hint=None):
        """
        agent_hint: 可选的 Agent 提示（用于路由）
        """
        features = self.backbone(input_ids, attention_mask)

        if agent_hint:
            # 直接使用指定 Agent 的头
            return self.heads[agent_hint](features)
        else:
            # 路由模式：返回所有头的预测
            return {name: head(features) for name, head in self.heads.items()}
```

#### 2.4.4 向后兼容策略

```python
# aiops/core/intent_model.py
class IntentModelManager:
    """
    模型管理器，支持多版本模型共存和渐进式迁移。
    """

    def __init__(self, config_path: str = "config/agents.yaml"):
        self.config = self._load_config(config_path)
        self.model_version = os.getenv("INTENT_MODEL_VERSION", "v1.0")

    def load_model(self):
        """加载指定版本的模型"""
        model_info = self.config["models"][self.model_version]

        if model_info["type"] == "lora":
            return self._load_lora_model(model_info["path"])
        elif model_info["type"] == "base":
            return self._load_base_model(model_info["path"])

    def get_supported_agents(self) -> list[str]:
        """获取当前模型支持的 Agent 列表"""
        model_info = self.config["models"][self.model_version]
        return model_info["supported_agents"]

    def classify(self, query: str) -> dict:
        """
        执行分类，自动处理不支持的 Agent。

        策略：
        1. 如果预测的 Agent 不在当前模型支持列表中
        2. 降级到关键词匹配
        3. 记录到 metrics（用于监控新 Agent 需求）
        """
        result = self._model_classify(query)
        predicted_agent = result["source"]

        # 检查是否支持
        supported = self.get_supported_agents()
        if predicted_agent not in supported:
            # 降级处理
            metrics = get_metrics()
            metrics.record_unsupported_agent(query, predicted_agent)

            # 使用关键词匹配
            return self._fallback_classify(query)

        return result

    def migrate_to_new_model(self, new_model_path: str):
        """
        迁移到新模型（支持更多 Agent）。

        流程：
        1. 加载新模型
        2. A/B 测试对比
        3. 逐步切换流量
        4. 监控错误率
        5. 完成切换
        """
        new_model = self._load_lora_model(new_model_path)

        # 并行运行
        self._run_parallel_validation(new_model)

        # 更新配置
        self._update_model_version(new_model_path)
```

#### 2.4.5 添加新 Agent 的流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    添加新 Agent 流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: 配置定义                                                 │
│  ├─ 在 config/agents.yaml 中添加新 Agent 定义                   │
│  ├─ 定义 keywords, examples, severity_levels                    │
│  └─ 设置 enabled: false（初始状态）                              │
│                                                                  │
│  Step 2: 数据准备                                                 │
│  ├─ 收集新 Agent 的示例查询（至少 50 条）                        │
│  ├─ 人工标注 source 和 severity                                 │
│  └─ 添加到训练集                                                │
│                                                                  │
│  Step 3: 增量训练                                                 │
│  ├─ 加载现有 LoRA 模型                                          │
│  ├─ 扩展输出层 (N → N+1 agents)                                 │
│  ├─ 在混合数据上微调（新数据 + 10% 旧数据）                     │
│  └─ 验证旧类别性能无回退                                         │
│                                                                  │
│  Step 4: 灰度发布                                                 │
│  ├─ 部署新模型到测试环境                                         │
│  ├─ A/B 测试（10% → 50% → 100%）                                │
│  ├─ 监控准确率和 Fallback 率                                     │
│  └─ 收集反馈并调整                                               │
│                                                                  │
│  Step 5: 正式发布                                                 │
│  ├─ 更新 config/agents.yaml 设置 enabled: true                  │
│  ├─ 更新模型版本号                                               │
│  └─ 通知用户新功能                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. 任务分解 (WBS)

### 3.1 Phase 1: 基础准备 (Week 1)

#### Task 1.1: 数据收集与清洗

**负责**: 待定 | **工期**: 1 天 | **优先级**: P0

**输出**:
- `scripts/collect_intent_data.py` - 数据收集脚本
- `data/raw_queries.jsonl` - 原始查询数据

**验收标准**:
- [ ] 从 `classification_metrics` 收集至少 500 条真实查询
- [ ] 去重、清洗、过滤无效数据
- [ ] 输出 JSONL 格式，每条包含 query, timestamp, metadata

**实现要点**:
```python
# scripts/collect_intent_data.py
def collect_queries(limit: int = 1000) -> list[dict]:
    """从 classification_metrics 收集历史查询"""
    metrics = get_metrics()
    records = metrics.get_recent_records(limit)

    cleaned = []
    seen = set()

    for record in records:
        # 去重
        query_hash = hashlib.md5(record.query.encode()).hexdigest()
        if query_hash in seen:
            continue
        seen.add(query_hash)

        # 过滤无效查询
        if len(record.query.strip()) < 5:
            continue

        cleaned.append({
            "query": record.query,
            "timestamp": record.timestamp,
            "method": record.method,
            "has_source": record.source is not None,
        })

    return cleaned
```

---

#### Task 1.2: 测试集标注

**负责**: 待定 | **工期**: 2 天 | **优先级**: P0

**输出**:
- `data/intent_test.jsonl` - 标注测试集 (200 条)
- `docs/annotation_guideline.md` - 标注规范文档

**验收标准**:
- [ ] 至少 200 条高质量标注数据
- [ ] 覆盖所有 5 个 source 和 4 个 severity
- [ ] 标注一致性 >90%

**数据格式**:
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

**标注规范**:
| Source | 触发关键词 | 示例查询 |
|--------|-----------|----------|
| metrics | cpu, memory, disk, network, 指标 | "CPU 使用率很高" |
| logs | log, error, exception, warning | "查看错误日志" |
| fault | 诊断, 根因, 异常, 崩溃 | "系统为什么崩溃" |
| security | 安全, 漏洞, 入侵, 权限 | "检查安全漏洞" |
| knowledge_base | 其他通用查询 | "如何配置监控" |

---

#### Task 1.3: 评估框架实现

**负责**: 待定 | **工期**: 1 天 | **优先级**: P0

**输出**:
- `aiops/core/intent_evaluator.py` - 评估器模块
- `tests/test_intent_evaluator.py` - 单元测试

**验收标准**:
- [ ] 实现 Accuracy, Precision, Recall, F1 计算
- [ ] 支持按 source/severity 分维度评估
- [ ] 生成混淆矩阵和分类报告
- [ ] 单元测试覆盖率 >80%

**接口设计**:
```python
class IntentEvaluator:
    def __init__(self, test_data_path: str):
        self.test_data = self._load_test_data(test_data_path)

    def evaluate(
        self,
        predictions: list[str],
        labels: list[str]
    ) -> EvaluationResult:
        """计算评估指标"""
        return EvaluationResult(
            accuracy=accuracy_score(labels, predictions),
            f1_macro=f1_score(labels, predictions, average="macro"),
            f1_micro=f1_score(labels, predictions, average="micro"),
            per_class_accuracy=self._calc_per_class_accuracy(...),
            confusion_matrix=confusion_matrix(labels, predictions),
        )

    def compare_models(
        self,
        model_a_predictions: list[str],
        model_b_predictions: list[str],
        labels: list[str]
    ) -> ComparisonReport:
        """对比两个模型的效果"""
        pass
```

---

#### Task 1.4: 基线测试

**负责**: 待定 | **工期**: 0.5 天 | **优先级**: P0

**输出**:
- `docs/baseline_report.md` - 基线评估报告

**验收标准**:
- [ ] 在测试集上评估当前 qwen2.5:3b 模型
- [ ] 记录准确率、F1、混淆矩阵
- [ ] 分析主要错误模式
- [ ] 确立优化基线

---

#### Task 1.5: 扩展性框架实现

**负责**: 待定 | **工期**: 1 天 | **优先级**: P1

**输出**:
- `aiops/core/agent_registry.py` - Agent 注册中心
- `config/agents.yaml` - Agent 配置文件
- `aiops/core/intent_model.py` - 模型管理器（支持多版本）

**验收标准**:
- [ ] 实现 Agent 注册机制，支持动态添加/查询
- [ ] 配置文件驱动，无需修改代码即可添加新 Agent
- [ ] 模型管理器支持版本切换和回滚
- [ ] 单元测试覆盖率 >80%

**实现要点**:
```python
# aiops/core/agent_registry.py
class AgentRegistry:
    """Agent 注册中心，支持动态扩展"""
    def register_agent(self, agent_def: AgentDefinition) -> None
    def unregister_agent(self, name: str) -> None
    def get_agent(self, name: str) -> AgentDefinition
    def list_agents(self) -> list[str]
    def get_num_labels(self) -> int  # 用于模型输出层

# config/agents.yaml
# 配置驱动的 Agent 定义
agents:
  metrics: { enabled: true, keywords: [...], priority: 1 }
  logs: { enabled: true, keywords: [...], priority: 2 }
  # 未来可扩展:
  # cost: { enabled: false, keywords: [...], priority: 6 }
```

**扩展性要求**:
- [ ] 添加新 Agent 时，仅修改配置文件和训练数据
- [ ] 支持模型热更新（不中断服务）
- [ ] 向后兼容（新 Agent 不影响现有分类）
- [ ] 渐进式迁移（A/B 测试 → 灰度 → 全量）

---

### 3.2 Phase 2: 自动化搜索 (Week 2)

#### Task 2.1: LLaMA-Factory 环境搭建

**负责**: 待定 | **工期**: 0.5 天 | **优先级**: P0

**输出**:
- `config/llamafactory_install.sh` - 安装脚本
- `config/llamafactory_base.yaml` - 基础配置

**验收标准**:
- [ ] 成功安装 LLaMA-Factory
- [ ] 配置 qwen2.5:3b 模型加载
- [ ] 验证 MPS 加速工作正常
- [ ] 运行简单测试训练

---

#### Task 2.2: 数据格式转换

**负责**: 待定 | **工期**: 1 天 | **优先级**: P0

**输出**:
- `scripts/convert_to_llamafactory.py` - 格式转换脚本
- `data/intent_train_llama.jsonl` - 训练集 (LLaMA-Factory 格式)
- `data/intent_val_llama.jsonl` - 验证集

**验收标准**:
- [ ] 支持从标注数据转换为 LLaMA-Factory 格式
- [ ] 支持 train/val 分割 (默认 8:2)
- [ ] 标签编码映射正确

**LLaMA-Factory 格式**:
```json
{
  "instruction": "你是一个 AIOps 系统的意图分类器。请分析以下查询并分类。",
  "input": "CPU 使用率很高，怎么办？",
  "output": "{\"source\": \"metrics\", \"severity\": \"medium\"}"
}
```

---

#### Task 2.3: 自动搜索模块开发

**负责**: 待定 | **工期**: 2 天 | **优先级**: P0

**输出**:
- `scripts/autosearch_intent.py` - 自动搜索主程序
- `config/search_space.yaml` - 搜索空间配置

**验收标准**:
- [ ] 实现随机搜索策略
- [ ] 支持时间预算控制 (30分钟/实验)
- [ ] 自动记录实验结果
- [ ] 支持断点续传

**核心实现**:
```python
class AutoSearchIntent:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.results = []
        self.best_result = None

    def search(self, time_budget_minutes: int = 30):
        """执行自动搜索"""
        start_time = time.time()

        iteration = 0
        while time.time() - start_time < time_budget_minutes * 60:
            iteration += 1

            # 采样配置
            config = self._sample_config()

            # 运行训练
            result = self._run_experiment(config)

            # 记录结果
            self.results.append(result)

            # 更新最优
            if self._is_better(result, self.best_result):
                self.best_result = result
                self._save_best_model(result)

        return self.best_result
```

---

#### Task 2.4: 基线微调实验

**负责**: 待定 | **工期**: 1 天 | **优先级**: P1

**输出**:
- `outputs/baseline_lora/` - 基线 LoRA 模型
- `docs/baseline_lora_report.md` - 实验报告

**验收标准**:
- [ ] 使用默认 LoRA 配置完成训练
- [ ] 在测试集上评估效果
- [ ] 与原始 qwen2.5:3b 对比
- [ ] 分析微调收益

---

### 3.3 Phase 3: 搜索执行 (Week 3)

#### Task 3.1: 自动搜索运行

**负责**: 待定 | **工期**: 3 天 | **优先级**: P0

**输出**:
- `outputs/search_results/` - 所有搜索结果
- `outputs/best_model/` - 最优模型

**验收标准**:
- [ ] 运行至少 10 次实验迭代
- [ ] 每次实验控制在 30 分钟内
- [ ] 记录完整的实验日志
- [ ] 生成搜索结果摘要

---

#### Task 3.2: 结果分析

**负责**: 待定 | **工期**: 1 天 | **优先级**: P0

**输出**:
- `docs/search_analysis_report.md` - 搜索分析报告
- `docs/parameter_sensitivity.md` - 参数敏感性分析

**验收标准**:
- [ ] 对比所有实验结果
- [ ] 分析参数对效果的影响
- [ ] 绘制学习曲线
- [ ] 提供最优配置建议

---

#### Task 3.3: 错误分析

**负责**: 待定 | **工期**: 1 天 | **优先级**: P1

**输出**:
- `docs/error_analysis.md` - 错误分析报告
- `data/error_cases.jsonl` - 错误案例集

**验收标准**:
- [ ] 分析最优模型的错误分类
- [ ] 按类别汇总错误模式
- [ ] 提出改进建议

---

### 3.4 Phase 4: 部署验证 (Week 4)

#### Task 4.1: 模型集成

**负责**: 待定 | **工期**: 1 天 | **优先级**: P0

**输出**:
- `aiops/core/intent_model.py` - 模型加载模块
- 修改 `router_workflow.py` 集成新模型

**验收标准**:
- [ ] 支持加载 LoRA 微调后的模型
- [ ] 保持与现有接口兼容
- [ ] 添加模型版本管理
- [ ] 支持快速回滚

**集成方案**:
```python
# aiops/core/intent_model.py
class IntentModelManager:
    def __init__(self):
        self.model_version = os.getenv("INTENT_MODEL_VERSION", "base")
        self.model_path = self._get_model_path()

    def load_model(self):
        """加载指定版本的意图识别模型"""
        if self.model_version == "base":
            return load_base_qwen()
        else:
            return load_lora_model(self.model_path)

    def classify(self, query: str) -> dict:
        """执行意图分类"""
        model = self.load_model()
        result = model(query)
        return {
            "source": result["source"],
            "severity": result["severity"],
            "model_version": self.model_version
        }
```

---

#### Task 4.2: A/B 测试

**负责**: 待定 | **工期**: 2 天 | **优先级**: P0

**输出**:
- `scripts/ab_test.py` - A/B 测试脚本
- `docs/ab_test_report.md` - A/B 测试报告

**验收标准**:
- [ ] 设计 A/B 测试方案
- [ ] 收集至少 100 条真实查询对比
- [ ] 统计显著性检验
- [ ] 生成对比报告

**A/B 测试设计**:
| 组别 | 模型 | 流量分配 | 评估指标 |
|------|------|----------|----------|
| Control | qwen2.5:3b (base) | 50% | 准确率, 延迟, Fallback率 |
| Treatment | qwen2.5:3b + LoRA | 50% | 同上 |

---

#### Task 4.3: 性能优化

**负责**: 待定 | **工期**: 1 天 | **优先级**: P1

**输出**:
- `docs/performance_report.md` - 性能报告

**验收标准**:
- [ ] 测量模型推理延迟
- [ ] 优化批处理策略
- [ ] 内存占用分析
- [ ] 确保满足生产要求 (延迟 <500ms)

---

#### Task 4.4: 文档与交付

**负责**: 待定 | **工期**: 1 天 | **优先级**: P0

**输出**:
- `docs/final_report.md` - 项目总结报告
- `docs/model_usage_guide.md` - 模型使用指南
- `config/production.yaml` - 生产配置

**验收标准**:
- [ ] 完整的项目总结
- [ ] 可复现的配置文档
- [ ] 部署检查清单
- [ ] 后续优化建议

---

## 4. 时间规划

### 4.1 甘特图

```
Week 1: 基础准备
├── Day 1-2:  Task 1.1 数据收集
├── Day 3-4:  Task 1.2 测试集标注
├── Day 5:    Task 1.3 评估框架
└── Day 5:    Task 1.4 基线测试

Week 2: 自动化
├── Day 6:    Task 2.1 LLaMA-Factory 搭建
├── Day 7:    Task 2.2 数据转换
├── Day 8-9:  Task 2.3 自动搜索开发
└── Day 10:   Task 2.4 基线微调

Week 3: 搜索执行
├── Day 11-13: Task 3.1 自动搜索运行
├── Day 14:    Task 3.2 结果分析
└── Day 15:    Task 3.3 错误分析

Week 4: 部署验证
├── Day 16:    Task 4.1 模型集成
├── Day 17-18: Task 4.2 A/B 测试
├── Day 19:    Task 4.3 性能优化
└── Day 20:    Task 4.4 文档交付
```

### 4.2 里程碑

| 里程碑 | 日期 | 交付物 | 验收标准 |
|--------|------|--------|----------|
| M1: 基准建立 | Day 5 | 测试集 + 基线报告 | 测试集 ≥200 条，基线准确率已知 |
| M2: 自动化就绪 | Day 10 | 搜索脚本 + 基线 LoRA | 脚本可运行，至少 1 次微调成功 |
| M3: 最优模型 | Day 15 | 最优模型 + 分析报告 | 准确率提升 >10% |
| M4: 生产就绪 | Day 20 | 集成模型 + 完整文档 | 通过 A/B 测试，文档完整 |

---

## 5. 风险管理

### 5.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 数据集不足 | 🟡 中 | 🔴 高 | 使用数据增强、迁移学习 |
| 微调效果不佳 | 🟡 中 | 🟡 中 | 扩大搜索空间、增加训练轮次 |
| LLaMA-Factory 兼容性 | 🟢 低 | 🟡 中 | 提前验证环境、备选方案 |
| Mac MPS 性能不足 | 🟡 中 | 🟡 中 | 降低 batch size、使用云 GPU |

### 5.2 项目风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 标注时间超期 | 🟡 中 | 🟡 中 | 预留缓冲、使用半监督标注 |
| 资源不足 | 🟢 低 | 🟡 中 | 优先级排序、云资源备用 |
| 时间延误 | 🟡 中 | 🟡 中 | 分阶段交付、MVP 优先 |

---

## 6. 资源需求

### 6.1 人力需求

| 角色 | 工作量 | 主要任务 |
|------|--------|----------|
| 算法工程师 | 40h | 方案设计、模型训练、评估分析 |
| 数据标注员 | 16h | 数据集标注 (200 条) |
| 后端工程师 | 8h | 模型集成、A/B 测试 |

### 6.2 计算资源

| 资源 | 配置 | 用途 | 时长 |
|------|------|------|------|
| Mac M1/M2/M3 | 16GB+ RAM | 开发、训练 | 持续 |
| GPU (可选) | A100 40GB | 加速训练 | 10-20h |

### 6.3 数据需求

| 数据类型 | 数量 | 来源 | 用途 |
|---------|------|------|------|
| 真实查询 | 500+ 条 | classification_metrics | 训练集 |
| 标注测试集 | 200 条 | 人工标注 | 评估基准 |
| 验证集 | 100 条 | 从训练集分割 | 超参调优 |

---

## 7. 成功标准

### 7.1 MVP 标准 (必须达成)

- ✅ 建立至少 200 条标注测试集
- ✅ 获得当前模型基线准确率
- ✅ 完成 LoRA 微调并评估
- ✅ 准确率提升 ≥ 5%

### 7.2 理想目标 (期望达成)

- 🎯 准确率提升 ≥ 10%
- 🎯 Fallback 率降低 ≥ 50%
- 🎯 平均延迟保持或降低
- 🎯 建立自动化搜索流程

### 7.3 降级方案

如果遇到无法克服的障碍：
- 仅完成提示词优化
- 输出分析报告，不部署模型
- 提供后续优化建议

---

## 8. 交付物清单

### 8.1 代码交付

- [ ] `scripts/collect_intent_data.py` - 数据收集
- [ ] `scripts/convert_to_llamafactory.py` - 格式转换
- [ ] `scripts/autosearch_intent.py` - 自动搜索
- [ ] `scripts/ab_test.py` - A/B 测试
- [ ] `aiops/core/intent_evaluator.py` - 评估器
- [ ] `aiops/core/intent_model.py` - 模型管理

### 8.2 配置交付

- [ ] `config/search_space.yaml` - 搜索空间
- [ ] `config/llamafactory_base.yaml` - 训练配置
- [ ] `config/production.yaml` - 生产配置

### 8.3 数据交付

- [ ] `data/raw_queries.jsonl` - 原始数据
- [ ] `data/intent_test.jsonl` - 测试集
- [ ] `data/intent_train_llama.jsonl` - 训练集
- [ ] `data/intent_val_llama.jsonl` - 验证集

### 8.4 文档交付

- [ ] `docs/annotation_guideline.md` - 标注规范
- [ ] `docs/baseline_report.md` - 基线报告
- [ ] `docs/search_analysis_report.md` - 搜索分析
- [ ] `docs/ab_test_report.md` - A/B 测试报告
- [ ] `docs/final_report.md` - 项目总结
- [ ] `docs/model_usage_guide.md` - 使用指南

---

## 9. 评审检查清单

### 9.1 方案评审 (执行前)

- [ ] **目标明确**: 目标与业务需求一致
- [ ] **方案可行**: 技术路径经过论证
- [ ] **资源充足**: 人力和资源已落实
- [ ] **时间合理**: 4 周时间线可接受
- [ ] **风险可控**: 主要风险有缓解措施

### 9.2 中期检查 (Week 2 结束)

- [ ] 数据集已准备就绪
- [ ] 基线测试已完成
- [ ] 自动搜索脚本可运行
- [ ] 无阻碍性问题

### 9.3 最终验收 (项目结束)

- [ ] 所有交付物已完成
- [ ] 效果提升可验证
- [ ] 文档完整可复现
- [ ] 代码和数据已归档

---

## 10. 下一步行动

### 10.1 立即行动 (评审通过后)

1. **确认资源**: 分配人力和计算资源
2. **建立环境**: 安装 LLaMA-Factory 和依赖
3. **开始数据收集**: 运行收集脚本获取历史查询

### 10.2 启动命令

```bash
# 1. 安装 LLaMA-Factory
pip install llama-factory

# 2. 收集数据
python -m scripts.collect_intent_data --output data/raw_queries.jsonl

# 3. 开始标注
python -m scripts.annotate_intents --input data/raw_queries.jsonl

# 4. 运行基线测试
python -m tests.intent_evaluation --baseline

# 5. 启动自动搜索
python -m scripts.autosearch_intent --config config/search_space.yaml
```

---

## 附录

### A. 参考资源

- [LLaMA-Factory 文档](https://github.com/hiyouga/LLaMA-Factory)
- [Qwen2.5 模型家族](https://huggingface.co/Qwen)
- [LoRA 论文](https://arxiv.org/abs/2106.09685)
- [autoresearch-macos](https://github.com/miolini/autoresearch-macos)

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
