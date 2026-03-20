"""Task decomposition using LLM-based analysis.

This module implements intelligent task decomposition that analyzes
complex user queries and breaks them down into executable subtasks
with proper dependency relationships.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Optional

from langchain_litellm import ChatLiteLLM
from pydantic import BaseModel, Field

from aiops.core.error_handler import get_logger
from aiops.core.events import EventBus
from aiops.tasks.events import (
    TaskDecompositionCompletedEvent,
    TaskDecompositionStartedEvent,
)
from aiops.tasks.models import (
    SubTask,
    TaskDecompositionResult,
    TaskExecutionPlan,
    TaskPriority,
    TaskStatus,
)
from aiops.workflows.complexity_analyzer import analyze_task_complexity

# Type alias for RouterState from router_workflow.py
RouterState = dict[str, Any]


class SubTaskDefinition(BaseModel):
    """Definition of a subtask from LLM output."""

    title: str = Field(description="Brief title of the subtask")
    description: str = Field(description="Detailed description of what to do")
    agent_type: str = Field(
        description="Type of agent: metrics, logs, fault, security, knowledge_base"
    )
    priority: str = Field(description="Priority: low, medium, high, critical")
    dependencies: list[str] = Field(
        description="List of task IDs this depends on (e.g., ['task_1'])",
        default_factory=list,
    )
    estimated_duration: int = Field(description="Estimated duration in seconds", default=30)


class DecompositionSchema(BaseModel):
    """Schema for LLM task decomposition output."""

    should_decompose: bool = Field(
        description="Whether the query is complex enough to warrant decomposition"
    )
    complexity_reasoning: str = Field(
        description="Explanation of why the query is or isn't complex"
    )
    subtasks: list[SubTaskDefinition] = Field(
        description="List of subtasks with their dependencies",
        default_factory=list,
    )


class TaskDecomposer:
    """Decomposes complex queries into executable subtasks.

    Uses LLM-based analysis to understand task complexity and
    generate appropriate subtask decompositions with dependency
    relationships.

    Attributes:
        llm: The LLM model used for decomposition analysis
        complexity_threshold: Score above which decomposition is triggered (0-1)
        max_subtasks: Maximum number of subtasks to generate
        timeout: LLM call timeout in seconds
        event_bus: EventBus for emitting progress events
    """

    def __init__(
        self,
        llm: ChatLiteLLM,
        complexity_threshold: float = 0.3,
        max_subtasks: int = 10,
        timeout: int = 30,
        event_bus: Optional[EventBus] = None,
    ):
        self.llm = llm
        self.complexity_threshold = complexity_threshold
        self.max_subtasks = max_subtasks
        self.timeout = timeout
        self.event_bus = event_bus
        self.logger = get_logger(__name__)

        # Valid agent types and priorities for validation
        self._valid_agents = {"metrics", "logs", "fault", "security", "knowledge_base"}
        self._valid_priorities = {"low", "medium", "high", "critical"}

    async def analyze_complexity(self, query: str) -> float:
        """Analyze query complexity using heuristic analysis.

        Args:
            query: The user query to analyze

        Returns:
            Complexity score between 0 and 1
        """
        state = {"query": query, "final_answer": ""}
        result = analyze_task_complexity(state, {"final_answer": ""})
        return result.get("complexity_score", 0.0)

    async def decompose(self, state: RouterState) -> TaskDecompositionResult:
        """Decompose a complex query into subtasks.

        Args:
            state: RouterState containing the query and context

        Returns:
            TaskDecompositionResult with subtasks and execution plan
        """
        query = state.get("query", "")
        plan_id = str(uuid.uuid4())

        # Emit start event
        if self.event_bus:
            self.event_bus.publish_nowait(
                TaskDecompositionStartedEvent(
                    timestamp=time.time(),
                    source="task_decomposer",
                    task_id=plan_id,
                    plan_id=plan_id,
                    query=query,
                )
            )

        start_time = time.perf_counter()

        try:
            # Step 1: Analyze complexity
            complexity_score = await self.analyze_complexity(query)
            self.logger.info(
                "complexity_analyzed",
                extra={
                    "query": query[:100],
                    "complexity_score": complexity_score,
                    "threshold": self.complexity_threshold,
                },
            )

            # Step 2: Decide whether to decompose
            if complexity_score < self.complexity_threshold:
                self.logger.info(
                    "simple_query_no_decomposition",
                    extra={"complexity_score": complexity_score},
                )
                result = TaskDecompositionResult(
                    should_decompose=False,
                    complexity_score=complexity_score,
                    reasoning=f"Complexity score {complexity_score:.2f} below threshold {self.complexity_threshold}",
                )

                if self.event_bus:
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    self.event_bus.publish_nowait(
                        TaskDecompositionCompletedEvent(
                            timestamp=time.time(),
                            source="task_decomposer",
                            task_id=plan_id,
                            plan_id=plan_id,
                            subtask_count=0,
                            complexity_score=complexity_score,
                            duration_ms=duration_ms,
                        )
                    )

                return result

            # Step 3: Use LLM to decompose
            subtasks = await self._llm_decompose(query, complexity_score)

            # Step 4: Build result
            result = TaskDecompositionResult(
                should_decompose=True,
                complexity_score=complexity_score,
                subtasks=subtasks,
                reasoning=f"Complexity score {complexity_score:.2f} warrants decomposition into {len(subtasks)} subtasks",
            )

            if self.event_bus:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                self.event_bus.publish_nowait(
                    TaskDecompositionCompletedEvent(
                        timestamp=time.time(),
                        source="task_decomposer",
                        task_id=plan_id,
                        plan_id=plan_id,
                        subtask_count=len(subtasks),
                        complexity_score=complexity_score,
                        duration_ms=duration_ms,
                    )
                )

            return result

        except Exception as e:
            self.logger.exception(
                "decomposition_failed",
                extra={"query": query[:100], "error": str(e)},
            )
            # Return simple decomposition on error
            return TaskDecompositionResult(
                should_decompose=False,
                complexity_score=0.0,
                reasoning=f"Decomposition failed: {str(e)[:100]}",
            )

    async def _llm_decompose(
        self, query: str, complexity_score: float
    ) -> list[SubTask]:
        """Use LLM to decompose the query into subtasks.

        Args:
            query: The user query to decompose
            complexity_score: Pre-computed complexity score

        Returns:
            List of SubTask objects with dependencies
        """
        # Build decomposition prompt
        decomposition_prompt = self._build_decomposition_prompt(query, complexity_score)

        try:
            # Call LLM
            response = await self._call_llm_with_timeout(decomposition_prompt)
            response_text = self._coerce_text(response.content)

            # Parse and validate
            schema = self._parse_llm_response(response_text)

            # Convert to SubTask objects
            subtasks = self._create_subtasks(schema)

            # Validate dependencies
            subtasks = self._validate_dependencies(subtasks)

            self.logger.info(
                "llm_decomposition_success",
                extra={
                    "subtask_count": len(subtasks),
                    "query": query[:100],
                },
            )

            return subtasks

        except Exception as e:
            self.logger.warning(
                "llm_decomposition_failed",
                extra={"error": str(e), "query": query[:100]},
            )
            # Fallback: create single task
            return self._create_fallback_subtasks(query)

    def _build_decomposition_prompt(self, query: str, complexity_score: float) -> list[dict]:
        """Build the LLM prompt for task decomposition.

        Supports both Chinese and English queries.
        """
        return [
            {
                "role": "system",
                "content": (
                    "你是一个 AIOps 任务分解专家。你的职责是分析复杂的运维查询，"
                    "将其分解为可执行的子任务，并识别任务之间的依赖关系。\n\n"
                    "**可用的代理类型:**\n"
                    "- metrics: 系统指标相关 (CPU、内存、磁盘、网络、Prometheus、监控数据)\n"
                    "- logs: 日志分析 (错误日志、异常堆栈、应用日志、系统日志)\n"
                    "- fault: 故障诊断 (根因分析、故障定位、系统异常诊断)\n"
                    "- security: 安全检查 (漏洞扫描、入侵检测、权限验证、安全审计)\n"
                    "- knowledge_base: 知识库查询 (文档检索、操作指南、最佳实践)\n\n"
                    "**依赖关系规则:**\n"
                    "- 收集数据的任务 (metrics, logs) 通常没有依赖，可以并行执行\n"
                    "- 分析任务 (fault) 通常依赖数据收集结果\n"
                    "- 安全检查 (security) 通常独立，可并行执行\n"
                    "- 使用 task_1, task_2 等格式引用依赖任务 ID\n\n"
                    "**输出格式:** 必须严格返回有效的 JSON 对象:\n"
                    '{\n'
                    '  "should_decompose": true,\n'
                    '  "complexity_reasoning": "解释为什么需要分解",\n'
                    '  "subtasks": [\n'
                    '    {\n'
                    '      "title": "简短的任务标题",\n'
                    '      "description": "详细描述任务要做什么",\n'
                    '      "agent_type": "metrics|logs|fault|security|knowledge_base",\n'
                    '      "priority": "low|medium|high|critical",\n'
                    '      "dependencies": ["task_1"],\n'
                    '      "estimated_duration": 30\n'
                    '    }\n'
                    '  ]\n'
                    '}\n\n'
                    "**重要:**\n"
                    "- 如果查询简单直接，设置 should_decompose 为 false\n"
                    "- 子任务数量不要超过 10 个\n"
                    "- 每个子任务的 estimated_duration 以秒为单位\n"
                    "- dependencies 列表中的 ID 必须在 subtasks 中存在\n"
                    "- 不要创建循环依赖\n"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"请分析以下查询并分解为子任务（支持中英文）:\n\n"
                    f"查询: {query}\n"
                    f"复杂度分数: {complexity_score:.2f}\n\n"
                    f"返回 JSON 对象:"
                ),
            },
        ]

    async def _call_llm_with_timeout(self, prompt: list[dict]) -> Any:
        """Call LLM with timeout protection."""
        import asyncio

        try:
            # For synchronous LLM, run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, self.llm.invoke, prompt),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"LLM decomposition call timed out after {self.timeout}s")

    @staticmethod
    def _coerce_text(value) -> str:
        """Safely coerce various types to string."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            if value and isinstance(value[0], dict) and "role" in value[0]:
                for msg in reversed(value):
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        return TaskDecomposer._coerce_text(msg.get("content"))
                return TaskDecomposer._coerce_text(value[-1].get("content") if isinstance(value[-1], dict) else value[-1])
            parts = []
            for item in value:
                if isinstance(item, dict):
                    if "text" in item:
                        parts.append(TaskDecomposer._coerce_text(item.get("text")))
                    elif "content" in item:
                        parts.append(TaskDecomposer._coerce_text(item.get("content")))
                    else:
                        parts.append(json.dumps(item, ensure_ascii=True))
                else:
                    parts.append(TaskDecomposer._coerce_text(item))
            return "\n".join([p for p in parts if p])
        if isinstance(value, dict):
            if "content" in value:
                return TaskDecomposer._coerce_text(value.get("content"))
            return json.dumps(value, ensure_ascii=True)
        return str(value)

    def _parse_llm_response(self, response_text: str) -> DecompositionSchema:
        """Parse LLM response into DecompositionSchema."""
        # Clean markdown code blocks
        cleaned = response_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Parse JSON
        data = json.loads(cleaned)

        # Validate with Pydantic
        return DecompositionSchema.model_validate(data)

    def _create_subtasks(self, schema: DecompositionSchema) -> list[SubTask]:
        """Convert DecompositionSchema to SubTask objects."""
        subtasks = []
        for idx, task_def in enumerate(schema.subtasks[: self.max_subtasks], 1):
            task_id = f"task_{idx}"

            # Validate agent_type
            agent_type = task_def.agent_type
            if agent_type not in self._valid_agents:
                agent_type = "knowledge_base"

            # Validate priority
            priority = task_def.priority
            if priority not in self._valid_priorities:
                priority = "medium"

            subtask = SubTask(
                id=task_id,
                title=task_def.title,
                description=task_def.description,
                agent_type=agent_type,
                priority=TaskPriority(priority),
                dependencies=task_def.dependencies,
                estimated_duration=task_def.estimated_duration,
            )
            subtasks.append(subtask)

        return subtasks

    def _validate_dependencies(self, subtasks: list[SubTask]) -> list[SubTask]:
        """Validate and fix dependency references.

        Ensures:
        - All dependency IDs exist in the subtask list
        - No circular dependencies
        """
        valid_ids = {t.id for t in subtasks}

        for task in subtasks:
            # Filter out invalid dependencies
            task.dependencies = [d for d in task.dependencies if d in valid_ids]

        # Detect cycles using simple DFS
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = next((t for t in subtasks if t.id == task_id), None)
            if task:
                for dep_id in task.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.remove(task_id)
            return False

        # Remove cycles by breaking dependencies
        for task in subtasks:
            if has_cycle(task.id):
                self.logger.warning(
                    "circular_dependency_detected",
                    extra={"task_id": task.id, "dependencies": task.dependencies},
                )
                task.dependencies.clear()

        return subtasks

    def _create_fallback_subtasks(self, query: str) -> list[SubTask]:
        """Create simple fallback subtasks when decomposition fails."""
        return [
            SubTask(
                id="task_1",
                title="Process query",
                description=f"Process the user query: {query[:100]}",
                agent_type="knowledge_base",
                priority=TaskPriority.medium,
                dependencies=[],
                estimated_duration=30,
            )
        ]


# Global instance factory
_decomposer_instance: Optional[TaskDecomposer] = None


def get_task_decomposer(
    llm: Optional[ChatLiteLLM] = None,
    event_bus: Optional[EventBus] = None,
) -> TaskDecomposer:
    """Get or create the global TaskDecomposer instance.

    Args:
        llm: Optional LLM instance (uses default if not provided)
        event_bus: Optional EventBus (uses global if not provided)

    Returns:
        TaskDecomposer instance
    """
    global _decomposer_instance

    if _decomposer_instance is None:
        if llm is None:
            # Create default LLM using environment variables
            model = os.getenv("ROUTER_LLM_MODEL", "ollama/qwen2.5:3b")
            api_base = os.getenv("LITELLM_API_BASE", "http://localhost:11434")
            llm = ChatLiteLLM(model=model, api_base=api_base)

        if event_bus is None:
            from aiops.core.events import get_event_bus
            event_bus = get_event_bus()

        complexity_threshold = float(os.getenv("TASK_DECOMPOSITION_THRESHOLD", "0.3"))
        max_subtasks = int(os.getenv("TASK_MAX_SUBTASKS", "10"))
        timeout = int(os.getenv("TASK_DECOMPOSITION_TIMEOUT", "30"))

        _decomposer_instance = TaskDecomposer(
            llm=llm,
            complexity_threshold=complexity_threshold,
            max_subtasks=max_subtasks,
            timeout=timeout,
            event_bus=event_bus,
        )

    return _decomposer_instance
