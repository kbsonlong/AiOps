# 任务分解与编排系统设计文档

> 版本: v1.0
> 创建时间: 2025-03-20
> 状态: ✅ 已实现

## 概述

任务分解与编排系统（Task Decomposition & Orchestration System）是 AIOps 项目的核心增强功能，旨在将复杂的用户查询自动分解为可执行的子任务，并实现依赖感知的并行编排执行。

### 核心能力

| 能力 | 描述 | 技术实现 |
|------|------|----------|
| **复杂度分析** | 评估查询复杂度 (0-1) + 决定是否分解 | 启发式规则 + LLM 评分 |
| **LLM 分解** | 将复杂查询分解为带依赖的子任务 | 结构化提示词 + JSON 解析 |
| **依赖编排** | 构建依赖图，计算拓扑排序 | NetworkX DiGraph |
| **并行执行** | 同层任务并行，跨层顺序执行 | asyncio.gather |
| **事件追踪** | 完整的执行进度事件流 | EventBus 发布/订阅 |

### 解决的问题

**Before（原有系统）**:
```
用户查询 → 分类 → 单个 Agent → 简单结果
❌ 无法处理多步骤任务
❌ 无依赖管理
❌ 无并行执行
```

**After（增强后）**:
```
用户查询 → 复杂度分析 → LLM 分解 → 依赖编排 → 并行执行
✅ 支持复杂多步骤任务
✅ 自动依赖管理
✅ 智能并行执行
```

---

## 系统架构

### 整体流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户查询输入                                  │
│                  "CPU 飙升，检查日志并诊断根因"                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      1. 复杂度分析 (ComplexityAnalyzer)              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ • 关键词匹配 (diagnose, analyze, multiple)                   │   │
│  │ • 子句数量分析                                               │   │
│  │ • 时间范围统计                                               │   │
│  │ • 技术关键词密度                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  复杂度分数: 0.72 (高于阈值 0.3，需要分解)                          │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      2. LLM 任务分解 (TaskDecomposer)                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 结构化提示词 → LLM → JSON 解析 → 验证                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  输出子任务:                                                         │
│  ┌────────┬──────────────┬─────────┬──────────────┐               │
│  │  ID    │    Title     │  Agent  │ Dependencies  │               │
│  ├────────┼──────────────┼─────────┼──────────────┤               │
│  │ task_1 │ 查询 CPU 指标 │ metrics │              │               │
│  │ task_2 │ 查询错误日志  │ logs    │              │               │
│  │ task_3 │ 分析根因      │ fault   │ task_1       │               │
│  │ task_4 │ 安全检查      │ security│              │               │
│  └────────┴──────────────┴─────────┴──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    3. 依赖图构建 (NetworkX)                          │
│                                                                      │
│       task_1 (metrics)         task_2 (logs)                        │
│            │                         │                               │
│            └──────────┬──────────────┘                               │
│                       │                                              │
│                       ▼                                              │
│                task_3 (fault)        task_4 (security)               │
│                                                                      │
│  拓扑层级:                                                           │
│  Layer 0: [task_1, task_2, task_4]  ← 并行执行                       │
│  Layer 1: [task_3]                  ← 等待 Layer 0 完成             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    4. 并行执行 (TaskOrchestrator)                     │
│                                                                      │
│  Layer 0 执行:                                                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                    │
│  │  task_1    │  │  task_2    │  │  task_4    │                    │
│  │  metrics   │  ��   logs     │  │  security  │                    │
│  │  5.2s ✓    │  │  3.1s ✓    │  │  2.8s ✓    │                    │
│  └────────────┘  └────────────┘  └────────────┘                    │
│         │               │               │                           │
│         └───────────────┴───────────────┘                           │
│                         │                                           │
│                         ▼                                           │
│  Layer 1 执行:                                                     │
│  ┌────────────┐                                                    │
│  │  task_3    │                                                    │
│  │   fault    │  ← 使用 task_1 的结果                               │
│  │  4.5s ✓    │                                                    │
│  └────────────┘                                                    │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        5. 结果合成                                   │
│  综合所有子任务结果，生成最终答案                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心组件

### 1. 数据模型 (`aiops/tasks/models.py`)

#### SubTask - 子任务模型

```python
class SubTask(BaseModel):
    """单个子任务定义"""

    id: str                          # 唯一标识: task_1, task_2, ...
    title: str                       # 简短标题
    description: str                 # 详细描述
    agent_type: str                  # 目标 Agent: metrics/logs/fault/...
    status: TaskStatus               # pending/in_progress/completed/failed
    priority: TaskPriority           # low/medium/high/critical
    dependencies: list[str]          # 依赖的任务 ID 列表
    estimated_duration: int | None   # 预估时长（秒）
    context: dict[str, Any]          # 执行上下文
    result: str | None               # 执行结果
    error: str | None                # 错误信息
    started_at: float | None         # 开始时间戳
    completed_at: float | None       # 完成时间戳

    @property
    def duration_ms(self) -> int | None:
        """计算实际执行时长"""
```

#### TaskExecutionPlan - 执行计划

```python
class TaskExecutionPlan(BaseModel):
    """任务执行计划"""

    query: str                                   # 原始查询
    subtasks: dict[str, SubTask]                 # 所有子任务 {id: SubTask}
    execution_layers: list[list[str]]            # 执行层级 [[tid1, tid2], [tid3]]
    total_estimated_duration: int                # 总预估时长
    created_at: float                            # 创建时间
    status: TaskStatus                           # 计划状态

    @property
    def total_subtasks(self) -> int:             # 总子任务数

    @property
    def completed_subtasks(self) -> int:         # 已完成数

    @property
    def progress_percent(self) -> float:         # 进度百分比
```

#### TaskDecompositionResult - 分解结果

```python
class TaskDecompositionResult(BaseModel):
    """任务分解结果"""

    should_decompose: bool                       # 是否需要分解
    complexity_score: float                      # 复杂度分数 (0-1)
    subtasks: list[SubTask]                      # 子任务列表
    reasoning: str                               # 分解决策说明
    execution_plan: TaskExecutionPlan | None     # 执行计划（可选）
```

### 2. 任务分解器 (`aiops/tasks/decomposer.py`)

```python
class TaskDecomposer:
    """LLM 驱动的任务分解器"""

    def __init__(
        self,
        llm: ChatLiteLLM,
        complexity_threshold: float = 0.3,      # 分解阈值
        max_subtasks: int = 10,                 # 最大子任务数
        timeout: int = 30,                      # LLM 超时
        event_bus: EventBus | None = None
    ):
        self.llm = llm
        self.complexity_threshold = complexity_threshold
        self.max_subtasks = max_subtasks
        self.timeout = timeout
        self.event_bus = event_bus

    async def analyze_complexity(self, query: str) -> float:
        """分析查询复杂度 (0-1)"""
        # 使用 ComplexityAnalyzer 进行启发式分析

    async def decompose(
        self,
        state: RouterState
    ) -> TaskDecompositionResult:
        """主分解流程"""
        # 1. 分析复杂度
        complexity_score = await self.analyze_complexity(query)

        # 2. 判断是否需要分解
        if complexity_score < self.complexity_threshold:
            return TaskDecompositionResult(
                should_decompose=False,
                complexity_score=complexity_score,
                reasoning="查询简单，无需分解"
            )

        # 3. LLM 分解
        subtasks = await self._llm_decompose(query, complexity_score)

        # 4. 验证依赖（检查循环）
        subtasks = self._validate_dependencies(subtasks)

        return TaskDecompositionResult(
            should_decompose=True,
            complexity_score=complexity_score,
            subtasks=subtasks
        )
```

#### LLM 分解提示词

```python
decomposition_prompt = [
    {
        "role": "system",
        "content": """
你是一个 AIOps 任务分解专家。分析复杂运维查询，分解为可执行的子任务。

**可用 Agent:**
- metrics: 系统指标 (CPU, 内存, Prometheus)
- logs: 日志分析 (错误, 异常, VictoriaLogs)
- fault: 故障诊断 (根因分析, 故障定位)
- security: 安全检查 (漏洞, 权限, 审计)
- knowledge_base: 知识库查询 (文档, 操作指南)

**依赖规则:**
- 数据收集任务 (metrics, logs) 无依赖，可并行
- 分析任务 (fault) 依赖数据收集结果
- 安全检查 (security) 通常独立

**输出格式 (JSON):**
{
  "should_decompose": true,
  "complexity_reasoning": "解释为什么需要分解",
  "subtasks": [
    {
      "title": "任务标题",
      "description": "详细描述",
      "agent_type": "metrics",
      "priority": "high",
      "dependencies": [],
      "estimated_duration": 30
    }
  ]
}
"""
    },
    {
        "role": "user",
        "content": f"查询: {query}\n复杂度: {complexity_score:.2f}\n返回 JSON:"
    }
]
```

### 3. 任务编排器 (`aiops/tasks/orchestrator.py`)

```python
class TaskOrchestrator:
    """依赖感知的任务编排器"""

    def __init__(
        self,
        event_bus: EventBus,
        composition_engine: SkillCompositionEngine | None = None
    ):
        self.event_bus = event_bus
        self.composition_engine = composition_engine or SkillCompositionEngine()

    def build_execution_plan(
        self,
        query: str,
        subtasks: list[SubTask]
    ) -> TaskExecutionPlan:
        """构建执行计划"""
        plan = TaskExecutionPlan(query=query)

        # 添加子任务
        for task in subtasks:
            plan.subtasks[task.id] = task

        # 构建依赖图
        graph = self._build_dependency_graph(subtasks)

        # 计算执行层级
        plan.execution_layers = self._compute_execution_layers(graph)

        return plan

    async def execute_plan(
        self,
        plan: TaskExecutionPlan,
        agent_map: dict[str, AgentExecutor]
    ) -> dict[str, str]:
        """执行计划"""
        results = {}

        for layer_idx, layer in enumerate(plan.execution_layers):
            # 并行执行同层任务
            layer_results = await self._execute_layer(
                plan, layer, layer_idx, agent_map
            )
            results.update(layer_results)

            # 检查是否需要中止
            if self._should_abort_on_failure(plan, layer_idx):
                break

        return results
```

#### 依赖图构建

```python
def _build_dependency_graph(
    self,
    subtasks: list[SubTask]
) -> nx.DiGraph:
    """使用 NetworkX 构建依赖图"""
    graph = nx.DiGraph()

    # 添加节点
    for task in subtasks:
        graph.add_node(task.id, task=task)

    # 添加边 (依赖关系)
    for task in subtasks:
        for dep_id in task.dependencies:
            if dep_id in graph.nodes:
                graph.add_edge(dep_id, task.id)

    return graph

def _compute_execution_layers(
    self,
    graph: nx.DiGraph
) -> list[list[str]]:
    """计算拓扑层级 (可并行的任务组)"""
    try:
        generations = list(nx.topological_generations(graph))
        return [list(layer) for layer in generations]
    except nx.NetworkXUnfeasible:
        # 有循环依赖，降级为顺序执行
        return [[node] for node in graph.nodes()]
```

### 4. 事件系统 (`aiops/tasks/events.py`)

```python
@dataclass(slots=True)
class TaskEvent(Event):
    """任务事件基类"""
    task_id: str
    plan_id: str

@dataclass(slots=True)
class TaskStartedEvent(TaskEvent):
    """任务开始执行"""
    task_title: str
    agent_type: str
    layer: int
    total_layers: int

@dataclass(slots=True)
class TaskCompletedEvent(TaskEvent):
    """任务完成"""
    task_title: str
    agent_type: str
    duration_ms: int
    result_length: int

@dataclass(slots=True)
class TaskFailedEvent(TaskEvent):
    """任务失败"""
    task_title: str
    agent_type: str
    error: str
    duration_ms: int
```

---

## 工作流集成

### Router Workflow 修改

#### 新增状态字段

```python
class RouterState(TypedDict):
    # ... 原有字段 ...
    task_decomposition: Optional[TaskDecompositionResult]
    execution_plan: Optional[TaskExecutionPlan]
```

#### 新增节点

```python
async def task_decompose_node(state: RouterState, config) -> dict:
    """任务分解节点"""
    decomposer = get_task_decomposer()
    result = await decomposer.decompose(state)
    return {"task_decomposition": result}

def task_route_dispatch(state: RouterState) -> list[Send]:
    """路由分发 - 根据分解结果决定执行路径"""
    decomposition = state.get("task_decomposition")

    if decomposition and decomposition.should_decompose:
        # 复杂任务 → 任务编排执行
        return [Send("task_execute", state)]

    # 简单任务 → 原有 Agent 路由
    classifications = state.get("classifications", [])
    return [Send(c["source"], {"query": c["query"]}) for c in classifications]

async def task_execute_node(state: RouterState, config) -> dict:
    """任务执行节点"""
    decomposition = state.get("task_decomposition")

    # 构建执行计划
    orchestrator = get_task_orchestrator()
    plan = orchestrator.build_execution_plan(
        query=state["query"],
        subtasks=decomposition.subtasks
    )

    # 执行计划
    agent_map = {}  # 实际应从 config 获取
    results = await orchestrator.execute_plan(plan, agent_map)

    # 合成结果
    answer = "任务执行完成:\n" + "\n".join(
        f"- {tid}: {res[:200]}..." for tid, res in results.items()
    )

    return {"final_answer": answer}
```

#### 工作流图更新

```python
graph = (
    StateGraph(RouterState)
    .add_node("classify", classify_query)
    .add_node("task_decompose", task_decompose_node)
    .add_node("task_execute", task_execute_node)
    .add_node("metrics", metrics_agent)
    .add_node("logs", logs_agent)
    # ... 其他节点 ...
    .add_edge("classify", "task_decompose")
    .add_conditional_edges(
        "task_decompose",
        task_route_dispatch,
        ["task_execute", "metrics", "logs", "fault", "security", "knowledge_base"]
    )
    .add_edge("task_execute", "synthesize")
    # ... 其他边 ...
)
```

---

## 使用示例

### 示例 1: 简单查询（不分解）

```python
query = "CPU 使用率是多少？"

# 复杂度分数: 0.15 (低于阈值 0.3)
# 路由决策: 不需要分解

# 执行路径:
# classify → task_decompose → route → metrics_agent → synthesize
```

### 示例 2: 复杂查询（分解执行）

```python
query = "CPU 使用率飙升，检查错误日志并诊断根因"

# 复杂度分数: 0.72 (高于阈值)
# 分解结果:
# - task_1: 查询 CPU 指标趋势 (metrics, 无依赖)
# - task_2: 查询错误日志 (logs, 无依赖)
# - task_3: 诊断根因 (fault, 依赖 task_1)
# - task_4: 安全检查 (security, 无依赖)

# 执行路径:
# classify → task_decompose → task_execute → synthesize

# 执行层级:
# Layer 0: [task_1, task_2, task_4] 并行执行
# Layer 1: [task_3] 等待 task_1 完成
```

### 示例 3: 代码调用

```python
from aiops.tasks import get_task_decomposer, get_task_orchestrator

# 初始化
decomposer = get_task_decomposer()
orchestrator = get_task_orchestrator()

# 分解任务
state = {"query": "诊断慢 API 问题"}
result = await decomposer.decompose(state)

if result.should_decompose:
    # 构建执行计划
    plan = orchestrator.build_execution_plan(
        query=state["query"],
        subtasks=result.subtasks
    )

    # 执行
    agent_map = {"metrics": metrics_executor, ...}
    results = await orchestrator.execute_plan(plan, agent_map)

    print(f"执行完成: {plan.get_summary()}")
```

---

## 配置参数

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TASK_DECOMPOSITION_THRESHOLD` | 0.3 | 复杂度阈值，高于此值才分解 |
| `TASK_MAX_SUBTASKS` | 10 | 最大子任务数量 |
| `TASK_DECOMPOSITION_TIMEOUT` | 30 | LLM 分解超时（秒） |

### LLM 模型选择

```bash
# 分解使用轻量级模型（更快）
ROUTER_LLM_MODEL=qwen3.5:2b

# Agent 执行使用较大模型（更准确）
LLM_MODEL=qwen3.5:9b
```

---

## 性能优化

### 1. 并行执行优势

```
顺序执行 (4 个任务，每个 5s):
task_1 → task_2 → task_3 → task_4 = 20s

并行执行 (2 层):
Layer 0: [task_1, task_2, task_4] = 5s
Layer 1: [task_3] = 5s
总计: 10s (50% 提升)
```

### 2. 缓存策略

```python
# 分解结果可缓存（相同查询）
@cache(ttl=3600)
async def decompose(state: RouterState) -> TaskDecompositionResult:
    ...
```

### 3. 超时控制

```python
# LLM 调用设置超时
try:
    result = await asyncio.wait_for(
        llm.invoke(prompt),
        timeout=30.0
    )
except asyncio.TimeoutError:
    # 降级到简单路由
```

---

## 监控与可观测性

### 指标追踪

```python
# 任务分解指标
- task_decomposition_total: 总分解次数
- task_decomposition_duration_ms: 分解耗时
- task_decomposition_complexity_score: 复杂度分数

# 任务执行指标
- task_execution_total: 总执行次数
- task_execution_duration_ms: 执行耗时
- task_execution_parallelism: 并行度
- task_failure_total: 失败次数
```

### 事件追踪示例

```
[TaskDecompositionStarted] query="诊断 API 慢问题"
[TaskDecompositionCompleted] subtasks=4, complexity=0.68, duration=850ms
[TaskPlanCreated] layers=2, total_duration=120s
[TaskLayerStarted] layer=0, tasks=3
[TaskStarted] task_1="查询 API 延迟", agent="metrics"
[TaskCompleted] task_1, duration=3200ms
[TaskLayerCompleted] layer=0, succeeded=3, failed=0, duration=5200ms
[TaskLayerStarted] layer=1, tasks=1
[TaskStarted] task_3="分析根因", agent="fault"
[TaskCompleted] task_3, duration=4500ms
[TaskPlanCompleted] total=8s, completed=4, failed=0
```

---

## 未来扩展

### 1. 智能子任务合并

```python
# 检测相似子任务，合并执行
if are_similar(task_1, task_2):
    merged_task = merge_tasks(task_1, task_2)
```

### 2. 自适应阈值

```python
# 根据历史数据动态调整分解阈值
threshold = calculate_adaptive_threshold(history)
```

### 3. 子任务重试

```python
# 失败子任务自动重试
if task.status == TaskStatus.failed:
    await retry_task(task, max_retries=3)
```

### 4. 人工审批

```python
# 高风险子任务需要人工批准
if task.risk_level == "critical":
    await request_approval(task)
```

---

## 相关文档

- [整体架构文档](./architecture.md)
- [Agent Skills 设计](./agent_skills_design.md)
- [架构优化提案](./architecture_optimization_proposals.md)

---

> 维护者: AIOps 团队
> 最后更新: 2025-03-20
