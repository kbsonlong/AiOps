需要做一套智能运维Agentix AI智能体，能够自动监控系统运行状态，及时发现异常情况并提供解决方案。
请设计一个智能运维基础框架，包括并且不限以下功能：
1. 自动监控系统运行状态，包括CPU、内存、磁盘、网络等指标。
2. 及时发现异常情况，例如CPU占用率过高、内存泄漏、磁盘空间不足等。
3. 提供解决方案，例如重启异常进程、增加磁盘空间、调整系统参数等。
4. 支持自定义监控指标和解决方案，例如监控自定义应用程序的运行状态、提供自定义的解决方案等。
5. 安全可控，确保智能体在监控和提供解决方案时不侵犯系统安全。
6. 可拓展性，方便添加新的监控指标和解决方案。
7. 多智能体协作，多个智能体可以协同工作，共同监控和解决系统异常。
## 意图识别优化

系统使用 **qwen2.5 系列模型** 实现快速精准的意图识别：

### 模型配置

| 用途 | 推荐模型 | 说明 |
|------|----------|------|
| 路由/意图识别 | `ollama/qwen2.5:3b` | 轻量级模型，快速分类用户意图 |
| 复杂任务执行 | `ollama/qwen2.5:7b` | 主模型，处理合成、代理执行等复杂任务 |

### 环境变量配置

```bash
# LiteLLM 多模型支持
LITELLM_API_BASE=http://localhost:11434  # Ollama 本地地址
LLM_MODEL=ollama/qwen2.5:7b              # 主 LLM
ROUTER_LLM_MODEL=ollama/qwen2.5:3b       # 路由 LLM

# 意图识别优化配置
ROUTER_TIMEOUT=15                         # 超时时间(秒)
ROUTER_MAX_TOKENS=512                     # 最大令牌数
ROUTER_TEMPERATURE=0                      # 温度(确定性输出)
```

### 降级机制

系统内置三层降级机制确保可用性：
1. **LLM 分类**：使用 qwen2.5:3b 进行智能意图分类
2. **关键词匹配**：LLM 调用失败时自动降级到关键词规则
3. **默认路由**：无法分类时默认路由到知识库

### 支持的意图类型

- **metrics**: 系统指标 (CPU、内存、磁盘、网络、负载)
- **logs**: 日志分析 (错误、异常、panic、warning)
- **fault**: 故障诊断 (根因分析、系统异常)
- **security**: 安全检查 (漏洞、入侵、权限)
- **knowledge_base**: 通用知识查询

### 支持的语言

- 中文 (zh)
- 英文 (en)
- 混合查询自动识别

## 意图识别统计

系统内置意图识别统计追踪功能，可量化 LLM 调用和 fallback 情况，便于性能分析和优化。

### 统计指标

- **LLM 调用次数**: 总调用、成功、失败
- **LLM 成功率**: 成功调用占比
- **Fallback 次数**: 降级到关键词匹配的次数
- **LLM 平均延迟**: 每次调用的平均响应时间
- **分类源分布**: 各代理类型的调用次数
- **严重程度分布**: 各严重级别的分类次数

### 查询统计

```bash
# 查看统计摘要
python -m aiops.tools.classification_stats

# 输出 JSON 格式
python -m aiops.tools.classification_stats --format json

# 查看最近 10 条记录
python -m aiops.tools.classification_stats --recent 10

# 重置统计数据
python -m aiops.tools.classification_stats --reset
```

### 编程方式

```python
from aiops.core.classification_metrics import get_metrics

# 获取统计实例
metrics = get_metrics()

# 获取统计信息
stats = metrics.get_stats()

# 打印摘要
print(stats.to_summary())

# 获取字典格式
data = stats.to_dict()

# 查看最近记录
recent = metrics.get_recent_records(100)
```

### 优化建议

根据统计数据分析：
- 如果 **LLM 成功率 < 80%**: 检查 LLM 服务稳定性或调整超时配置
- 如果 **LLM 平均延迟 > 1000ms**: 考虑使用更小的模型或优化提示词
- 如果 **Fallback 次数过高**: 可能需要增强提示词或检查 LLM 输出格式
