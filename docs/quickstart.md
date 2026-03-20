# AIOps 快速入门指南

> 版本: v2.0
> 更新时间: 2025-03-20

## 目录

1. [环境准备](#环境准备)
2. [快速安装](#快速安装)
3. [基本使用](#基本使用)
4. [任务分解示例](#任务分解示例)
5. [常用命令](#常用命令)
6. [故障排查](#故障排查)

---

## 环境准备

### 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| Python | 3.12+ | 3.12.8 |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 10GB | 50GB+ |
| CPU | 2核 | 4核+ |

### 外部依赖

| 服务 | 用途 | 是否必需 |
|------|------|---------|
| LLM 服务 | 模型推理 | 必需 |
| Redis | 缓存 | 可选 |
| Chroma | 向量数据库 | 可选 |

---

## 快速安装

### 1. 克隆项目

```bash
git clone https://github.com/your-org/aiops.git
cd aiops
```

### 2. 安装依赖

```bash
# 使用 uv (推荐)
pip install uv
uv sync

# 或使用 pip
pip install -e .
```

### 3. 配置 LLM

#### 使用 Ollama (本地)

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

#### 使用 LiteLLM (云服务)

```bash
# 设置环境变量
export LITELLM_API_BASE="https://api.openai.com/v1"
export LITELLM_API_KEY="your-api-key"
export LLM_MODEL="gpt-4"
```

### 4. 配置环境变量

创建 `.env` 文件：

```bash
# LLM 配置
ROUTER_LLM_MODEL=qwen2.5:3b
LLM_MODEL=qwen2.5:7b
LITELLM_API_BASE=http://localhost:11434

# 任务分解配置
TASK_DECOMPOSITION_THRESHOLD=0.3
TASK_MAX_SUBTASKS=10
TASK_DECOMPOSITION_TIMEOUT=30

# 缓存配置
AIOPS_CACHE__ENABLED=true
AIOPS_CACHE__DEFAULT_TTL_SEC=3600
```

### 5. 验证安装

```bash
python -c "from aiops import build_default_workflow; print('安装成功!')"
```

---

## 基本使用

### Python 交互式

```python
from aiops.workflows.router_workflow import build_default_workflow

# 构建工作流
workflow = build_default_workflow()

# 执行查询
state = {
    "query": "CPU 使用率是多少？",
    "classifications": [],
    "results": [],
    "final_answer": "",
    "context": {},
    "detected_skills": [],
    "skill_execution_plan": {},
}

result = await workflow.ainvoke(state)
print(result["final_answer"])
```

### 命令行 (如果可用)

```bash
# 启动交互式 CLI
aiops-cli

# 或直接查询
aiops-cli query "CPU 使用率是多少？"
```

---

## 任务分解示例

### 简单查询（不分解）

```python
from aiops.tasks import get_task_decomposer

decomposer = get_task_decomposer()

state = {"query": "CPU 使用率是多少？"}
result = await decomposer.decompose(state)

print(f"需要分解: {result.should_decompose}")  # False
print(f"复杂度: {result.complexity_score}")    # 0.15
```

### 复杂查询（自动分解）

```python
state = {"query": "CPU 使用率飙升，检查错误日志并诊断根因"}
result = await decomposer.decompose(state)

print(f"需要分解: {result.should_decompose}")  # True
print(f"复杂度: {result.complexity_score}")    # 0.72

# 查看子任务
for task in result.subtasks:
    print(f"- {task.id}: {task.title}")
    print(f"  Agent: {task.agent_type}")
    print(f"  依赖: {task.dependencies}")

# 输出:
# - task_1: 查询 CPU 指标趋势
#   Agent: metrics
#   依赖: []
# - task_2: 查询错误日志
#   Agent: logs
#   依赖: []
# - task_3: 分析根因
#   Agent: fault
#   依赖: ['task_1']
# - task_4: 安全检查
#   Agent: security
#   依赖: []
```

### 执行分解后的任务

```python
from aiops.tasks import get_task_orchestrator

orchestrator = get_task_orchestrator()

# 构建执行计划
plan = orchestrator.build_execution_plan(
    query=state["query"],
    subtasks=result.subtasks
)

# 查看执行层级
for i, layer in enumerate(plan.execution_layers):
    print(f"Layer {i}: {layer}")

# 输出:
# Layer 0: ['task_1', 'task_2', 'task_4']  # 并行执行
# Layer 1: ['task_3']                      # 等待 task_1

# 执行计划
agent_map = {}  # 实际应传入 Agent 执行器
results = await orchestrator.execute_plan(plan, agent_map)

# 查看执行摘要
print(plan.get_summary())
```

---

## 常用命令

### 技能管理

```bash
# 列出所有技能
aiops-cli skills list

# 注册新技能
aiops-cli skills register skill_definition.yaml

# 删除技能
aiops-cli skills remove skill_id

# 测试技能
aiops-cli skills test skill_id
```

### 配置管理

```bash
# 验证配置
aiops-cli config validate

# 查看当前配置
aiops-cli config show

# 重新加载配置
aiops-cli config reload
```

### 健康检查

```bash
# 检查系统状态
aiops-cli health check

# 查看组件状态
aiops-cli health components
```

---

## 配置文件示例

### 完整配置 (`config.yaml`)

```yaml
app_name: "aiops-agent"
environment: "production"
log_level: "INFO"
data_dir: "data"

# 缓存配置
cache:
  enabled: true
  default_ttl_sec: 3600
  max_entries: 2048
  backend: "memory"  # or "redis"

  redis:
    host: "localhost"
    port: 6379
    db: 0

# 指标收集
metrics:
  enabled: true
  collect_latency: true
  track_success_rate: true
  export_to_prometheus: false

# 技能配置
skills:
  auto_discovery: true
  sandbox_enabled: true
  quality_threshold: 0.7
  max_execution_time: 300

# 知识库配置
knowledge:
  chroma_path: "data/chroma"
  embeddings_model: "text-embedding-ada-002"
  chunk_size: 1000
  chunk_overlap: 200

# 安全配置
security:
  encryption_enabled: false
  audit_log_enabled: true
  approval_required_for_critical: true
```

---

## 故障排查

### LLM 连接失败

```bash
# 检查 Ollama 服务
curl http://localhost:11434/api/tags

# 检查模型是否下载
ollama list

# 测试 LLM 调用
python -c "
from langchain_litellm import ChatLiteLLM
llm = ChatLiteLLM(model='qwen2.5:3b', api_base='http://localhost:11434')
print(llm.invoke('Hello').content)
"
```

### 任务分解不工作

```python
# 检查复杂度阈值
from aiops.tasks import get_task_decomposer
decomposer = get_task_decomposer()

# 查看当前阈值
print(decomposer.complexity_threshold)  # 默认 0.3

# 降低阈值测试
decomposer.complexity_threshold = 0.1
```

### Agent 执行失败

```bash
# 检查日志
tail -f logs/aiops.log

# 启用调试模式
export LOG_LEVEL=DEBUG
python main.py
```

### 性能问题

```python
# 检查执行层级
print(plan.execution_layers)

# 查看任务耗时
for task_id, task in plan.subtasks.items():
    if task.duration_ms:
        print(f"{task_id}: {task.duration_ms}ms")
```

---

## 下一步

- 阅读 [完整架构文档](./architecture.md)
- 查看 [API 参考](./api_reference.md)
- 了解 [任务分解系统](./task_orchestration_design.md)
- 探索 [Agent Skills 设计](./agent_skills_design.md)

---

## 获取帮助

- GitHub Issues: https://github.com/your-org/aiops/issues
- 文档: https://docs.aiops.example.com
- 邮件: support@aiops.example.com

---

> 维护者: AIOps 团队
> 最后更新: 2025-03-20
