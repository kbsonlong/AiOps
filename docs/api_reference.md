# AIOps API 参考

> 版本: v2.0
> 更新时间: 2025-03-20

## 目录

1. [任务系统 API](#任务系统-api)
2. [Agent API](#agent-api)
3. [Skills API](#skills-api)
4. [Workflow API](#workflow-api)
5. [事件系统 API](#事件系统-api)
6. [配置 API](#配置-api)

---

## 任务系统 API

### 模块: `aiops.tasks`

#### 核心类

##### `TaskDecomposer`

```python
class TaskDecomposer:
    """LLM 驱动的任务分解器"""

    def __init__(
        self,
        llm: ChatLiteLLM,
        complexity_threshold: float = 0.3,
        max_subtasks: int = 10,
        timeout: int = 30,
        event_bus: EventBus | None = None
    ) -> None:
        """
        初始化任务分解器。

        Args:
            llm: 用于分解的 LLM 模型
            complexity_threshold: 复杂度阈值 (0-1)，高于此值才分解
            max_subtasks: 最大子任务数量
            timeout: LLM 调用超时时间（秒）
            event_bus: 事件总线（可选）
        """

    async def analyze_complexity(self, query: str) -> float:
        """
        分析查询复杂度。

        Args:
            query: 用户查询文本

        Returns:
            复杂度分数 (0-1)，越接近 1 越复杂
        """

    async def decompose(
        self,
        state: RouterState
    ) -> TaskDecompositionResult:
        """
        分解任务。

        Args:
            state: RouterState 包含查询和上下文

        Returns:
            TaskDecompositionResult 分解结果
        """
```

##### `TaskOrchestrator`

```python
class TaskOrchestrator:
    """依赖感知的任务编排器"""

    def __init__(
        self,
        event_bus: EventBus,
        composition_engine: SkillCompositionEngine | None = None
    ) -> None:
        """
        初始化任务编排器。

        Args:
            event_bus: 事件总线
            composition_engine: 技能组合引擎（可选）
        """

    def build_execution_plan(
        self,
        query: str,
        subtasks: list[SubTask]
    ) -> TaskExecutionPlan:
        """
        构建执行计划。

        Args:
            query: 原始查询
            subtasks: 子任务列表

        Returns:
            TaskExecutionPlan 执行计划
        """

    async def execute_plan(
        self,
        plan: TaskExecutionPlan,
        agent_map: dict[str, AgentExecutor]
    ) -> dict[str, str]:
        """
        执行计划。

        Args:
            plan: 执行计划
            agent_map: Agent 执行器映射 {agent_type: executor}

        Returns:
            dict[str, str] 任务结果 {task_id: result}
        """

    def get_progress(
        self,
        plan: TaskExecutionPlan
    ) -> TaskProgress:
        """
        获取执行进度。

        Args:
            plan: 执行计划

        Returns:
            TaskProgress 进度信息
        """
```

#### 数据模型

##### `SubTask`

```python
class SubTask(BaseModel):
    """子任务模型"""

    id: str                              # 任务 ID
    title: str                           # 标题
    description: str                     # 描述
    agent_type: str                      # Agent 类型
    status: TaskStatus                   # 状态
    priority: TaskPriority               # 优先级
    dependencies: list[str]              # 依赖
    estimated_duration: int | None       # 预估时长
    context: dict[str, Any]              # 上下文
    result: str | None                   # 结果
    error: str | None                    # 错误

    def mark_started(self) -> None:      """标记为开始"""
    def mark_completed(self, result: str | None = None) -> None:  """标记为完成"""
    def mark_failed(self, error: str) -> None:  """标记为失败"""
    def mark_skipped(self) -> None:       """标记为跳过"""

    @property
    def duration_ms(self) -> int | None:  """获取执行时长"""
```

##### `TaskExecutionPlan`

```python
class TaskExecutionPlan(BaseModel):
    """执行计划"""

    query: str
    subtasks: dict[str, SubTask]
    execution_layers: list[list[str]]
    total_estimated_duration: int
    created_at: float
    status: TaskStatus

    @property
    def total_subtasks(self) -> int

    @property
    def completed_subtasks(self) -> int

    @property
    def failed_subtasks(self) -> int

    @property
    def progress_percent(self) -> float

    def get_subtask(self, task_id: str) -> SubTask | None

    def get_ready_tasks(self) -> list[SubTask]

    def get_summary(self) -> dict[str, Any]
```

##### `TaskDecompositionResult`

```python
class TaskDecompositionResult(BaseModel):
    """任务分解结果"""

    should_decompose: bool
    complexity_score: float
    subtasks: list[SubTask]
    reasoning: str
    execution_plan: TaskExecutionPlan | None

    @property
    def subtask_count(self) -> int
```

##### 枚举类型

```python
class TaskStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"

class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"
```

#### 工厂函数

```python
def get_task_decomposer(
    llm: ChatLiteLLM | None = None,
    event_bus: EventBus | None = None
) -> TaskDecomposer:
    """
    获取或创建全局 TaskDecomposer 实例。

    Args:
        llm: LLM 模型（默认使用环境变量配置）
        event_bus: 事件总线（默认使用全局实例）

    Returns:
        TaskDecomposer 实例
    """

def get_task_orchestrator(
    event_bus: EventBus | None = None
) -> TaskOrchestrator:
    """
    获取或创建全局 TaskOrchestrator 实例。

    Args:
        event_bus: 事件总线（默认使用全局实例）

    Returns:
        TaskOrchestrator 实例
    """
```

---

## Agent API

### 模块: `aiops.agents`

#### Agent 类

##### `MetricsAgent`

```python
class MetricsAgent:
    """系统指标监控 Agent"""

    def build(self, llm) -> Agent:
        """构建 LangChain Agent"""

    @staticmethod
    def get_system_prompt() -> str:
        """获取系统提示词"""

    @staticmethod
    def get_tools() -> list[BaseTool]:
        """获取可用工具"""
```

##### `LogsAgent`, `FaultAgent`, `SecurityAgent`

接口同 `MetricsAgent`。

##### `KnowledgeAgent`

```python
class KnowledgeAgent:
    """知识库查询 Agent (RAG)"""

    def __init__(self, vector_store: VectorStoreManager):
        """
        初始化知识库 Agent。

        Args:
            vector_store: 向量存储管理器
        """

    def build(self, llm) -> Agent:
        """构建 LangChain Agent"""

    async def query_knowledge(
        self,
        query_text: str,
        k: int = 4
    ) -> list[Document]:
        """
        查询知识库。

        Args:
            query_text: 查询文本
            k: 返回文档数量

        Returns:
            相关文档列表
        """
```

#### 工厂函数

```python
def build_metrics_agent() -> MetricsAgent:
    """构建 Metrics Agent"""

def build_logs_agent() -> LogsAgent:
    """构建 Logs Agent"""

def build_fault_agent() -> FaultAgent:
    """构建 Fault Agent"""

def build_security_agent() -> SecurityAgent:
    """构建 Security Agent"""
```

---

## Skills API

### 模块: `aiops.skills`

#### 核心类

##### `SkillDefinition`

```python
class SkillDefinition(BaseModel):
    """技能定义"""

    id: str                              # 技能 ID
    name: str                            # 技能名称
    category: SkillCategory              # 分类
    description: str                     # 描述
    risk_level: SkillRiskLevel           # 风险等级
    dependencies: list[str]              # 依赖技能
    metadata: dict[str, Any]             # 元数据
```

##### `SkillRegistry`

```python
class SkillRegistry:
    """技能注册表"""

    def register(self, skill: SkillDefinition) -> None:
        """注册技能"""

    def unregister(self, skill_id: str) -> None:
        """注销技能"""

    def get(self, skill_id: str) -> SkillDefinition | None:
        """获取技能"""

    def list_by_category(
        self,
        category: SkillCategory
    ) -> list[SkillDefinition]:
        """按类别列出技能"""

    def find_by_risk_level(
        self,
        risk_level: SkillRiskLevel
    ) -> list[SkillDefinition]:
        """按风险等级查找技能"""
```

##### `SkillCompositionEngine`

```python
class SkillCompositionEngine:
    """技能组合引擎"""

    def build_execution_plan(
        self,
        skills: list[SkillDefinition],
        context: dict | None = None
    ) -> SkillExecutionPlan:
        """
        构建技能执行计划。

        Args:
            skills: 技能列表
            context: 执行上下文

        Returns:
            SkillExecutionPlan 执行计划
        """
```

#### 枚举类型

```python
class SkillCategory(str, Enum):
    MONITORING = "monitoring"
    DIAGNOSIS = "diagnosis"
    REMEDIATION = "remediation"
    NOTIFICATION = "notification"
    SECURITY = "security"
    KNOWLEDGE = "knowledge"

class SkillRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

---

## Workflow API

### 模块: `aiops.workflows.router_workflow`

#### 主要函数

##### `build_workflow`

```python
def build_workflow(
    llm: ChatLiteLLM,
    router_llm: ChatLiteLLM,
    settings: Settings | None = None
) -> CompiledStateGraph:
    """
    构建路由工作流。

    Args:
        llm: 主 LLM（用于 Agent 执行）
        router_llm: 路由 LLM（用于分类和分解）
        settings: 配置对象（可选）

    Returns:
        CompiledStateGraph 编译后的工作流
    """
```

##### `build_default_workflow`

```python
def build_default_workflow() -> CompiledStateGraph:
    """
    构建默认工作流（使用环境变量配置）。

    Returns:
        CompiledStateGraph 编译后的工作流
    """
```

#### 状态类型

##### `RouterState`

```python
class RouterState(TypedDict):
    query: str
    classifications: list[Classification]
    results: Annotated[list[AgentOutput], operator.add]
    final_answer: str
    context: dict
    detected_skills: list[dict]
    skill_execution_plan: dict
    knowledge_context: str | None
    knowledge_base_result: str | None
    task_decomposition: TaskDecompositionResult | None
    execution_plan: TaskExecutionPlan | None
```

##### `Classification`

```python
class Classification(TypedDict):
    source: Source                # metrics, logs, fault, security, knowledge_base
    query: str                    # 针对该 Agent 的子查询
    severity: Severity            # low, medium, high, critical
```

---

## 事件系统 API

### 模块: `aiops.core.events`

#### 核心类

##### `EventBus`

```python
class EventBus:
    """事件总线"""

    def subscribe(
        self,
        event_type: Type[TEvent],
        handler: EventHandler[TEvent]
    ) -> Callable[[], None]:
        """
        订阅事件。

        Args:
            event_type: 事件类型
            handler: 事件处理器

        Returns:
            取消订阅的函数
        """

    def unsubscribe(
        self,
        event_type: Type[TEvent],
        handler: EventHandler[TEvent]
    ) -> None:
        """
        取消订阅。

        Args:
            event_type: 事件类型
            handler: 事件处理器
        """

    async def publish(self, event: Event) -> None:
        """
        发布事件。

        Args:
            event: 事件对象
        """

    def publish_nowait(self, event: Event) -> None:
        """
        非阻塞发布事件。

        Args:
            event: 事件对象
        """
```

#### 工厂函数

```python
def get_event_bus() -> EventBus:
    """获取全局 EventBus 实例"""
```

### 模块: `aiops.tasks.events`

#### 任务事件类型

```python
@dataclass(slots=True)
class TaskEvent(Event):
    """任务事件基类"""
    task_id: str
    plan_id: str

@dataclass(slots=True)
class TaskDecompositionStartedEvent(TaskEvent):
    """任务分解开始"""
    query: str

@dataclass(slots=True)
class TaskDecompositionCompletedEvent(TaskEvent):
    """任务分解完成"""
    subtask_count: int
    complexity_score: float
    duration_ms: int

@dataclass(slots=True)
class TaskStartedEvent(TaskEvent):
    """任务开始"""
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

## 配置 API

### 模块: `aiops.config.settings`

#### 类

##### `Settings`

```python
class Settings(BaseModel):
    """根配置模型"""

    app_name: str = Field(default="aiops-agent")
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    data_dir: str = Field(default="data")
    cache: CacheConfig = Field(default_factory=CacheConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    logs: LogsConfig = Field(default_factory=LogsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
```

##### `CacheConfig`, `MetricsConfig`, 等

子配置模型，详见各配置文件。

#### 函数

##### `load_settings`

```python
def load_settings(
    config_path: str | Path | None = None,
    env_prefix: str = "AIOPS_"
) -> Settings:
    """
    加载配置。

    Args:
        config_path: 配置文件路径（可选）
        env_prefix: 环境变量前缀

    Returns:
        Settings 配置对象
    """
```

##### `ConfigManager`

```python
class ConfigManager:
    """配置管理器（支持热重载）"""

    def __init__(
        self,
        config_path: str | Path | None = None,
        env_prefix: str = "AIOPS_"
    ) -> None:
        """初始化配置管理器"""

    def reload(self) -> Settings:
        """重新加载配置"""

    def check_reload(self) -> bool:
        """检查文件变化并自动重载"""
```

---

## 使用示例

### 完整工作流调用

```python
from aiops.workflows.router_workflow import build_default_workflow

# 构建工作流
workflow = build_default_workflow()

# 执行
state = {
    "query": "CPU 使用率飙升，检查日志并诊断根因",
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

### 任务分解与执行

```python
from aiops.tasks import get_task_decomposer, get_task_orchestrator

# 初始化
decomposer = get_task_decomposer()
orchestrator = get_task_orchestrator()

# 分解
state = {"query": "诊断 API 慢问题"}
decomposition = await decomposer.decompose(state)

if decomposition.should_decompose:
    # 构建计划
    plan = orchestrator.build_execution_plan(
        query=state["query"],
        subtasks=decomposition.subtasks
    )

    # 执行
    agent_map = {"metrics": metrics_executor, "logs": logs_executor}
    results = await orchestrator.execute_plan(plan, agent_map)

    print(f"完成: {plan.progress_percent:.1f}%")
```

### 事件订阅

```python
from aiops.core.events import get_event_bus
from aiops.tasks.events import TaskCompletedEvent

event_bus = get_event_bus()

def on_task_completed(event: TaskCompletedEvent):
    print(f"任务完成: {event.task_title} ({event.duration_ms}ms)")

# 取消函数
unsubscribe = event_bus.subscribe(
    TaskCompletedEvent,
    on_task_completed
)

# 发布事件
event_bus.publish_nowait(
    TaskCompletedEvent(
        timestamp=time.time(),
        source="task_orchestrator",
        task_id="task_1",
        plan_id="plan_123",
        task_title="查询 CPU",
        agent_type="metrics",
        duration_ms=1500,
        result_length=256
    )
)

# 取消订阅
unsubscribe()
```

---

## 类型定义

### Agent 类型

```python
Source = Literal[
    "metrics",
    "logs",
    "fault",
    "security",
    "knowledge_base"
]
```

### 严重程度

```python
Severity = Literal["low", "medium", "high", "critical"]
```

### 用户意图

```python
UserIntent = Literal["consultation", "operation"]
```

---

## 异常类型

```python
class AgentException(AiOpsException):
    """Agent 异常基类"""

class TaskDecompositionException(AiOpsException):
    """任务分解异常"""

class TaskExecutionException(AiOpsException):
    """任务执行异常"""

class SkillExecutionException(AiOpsException):
    """技能执行异常"""
```

---

> 维护者: AIOps 团队
> 最后更新: 2025-03-20
