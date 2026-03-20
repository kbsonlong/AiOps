"""Task orchestration with dependency-aware execution.

This module implements the TaskOrchestrator that manages the execution
of decomposed tasks using topological sorting for parallel execution
while respecting dependency relationships.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable

import networkx as nx

from aiops.core.error_handler import get_logger
from aiops.core.events import EventBus
from aiops.skills.composition import SkillCompositionEngine
from aiops.tasks.events import (
    TaskCompletedEvent,
    TaskEvent,
    TaskFailedEvent,
    TaskLayerCompletedEvent,
    TaskLayerStartedEvent,
    TaskPlanCompletedEvent,
    TaskPlanCreatedEvent,
    TaskSkippedEvent,
    TaskStartedEvent,
)
from aiops.tasks.models import (
    SubTask,
    TaskExecutionPlan,
    TaskProgress,
    TaskStatus,
)

# Type alias for agent execution function
AgentExecutor = Callable[[str, str, dict[str, Any]], str | None]


class TaskOrchestrator:
    """Orchestrates task execution with dependency management.

    Uses NetworkX to build dependency graphs and compute optimal
    execution order with parallel processing of independent tasks.

    Attributes:
        event_bus: EventBus for emitting progress events
        composition_engine: Reused from skills for topological sorting
        logger: Logger instance
    """

    def __init__(
        self,
        event_bus: EventBus,
        composition_engine: SkillCompositionEngine | None = None,
    ):
        self.event_bus = event_bus
        self.composition_engine = composition_engine or SkillCompositionEngine()
        self.logger = get_logger(__name__)

    def build_execution_plan(
        self,
        query: str,
        subtasks: list[SubTask],
    ) -> TaskExecutionPlan:
        """Build an execution plan from subtasks.

        Creates a dependency graph and computes topological layers
        for parallel execution.

        Args:
            query: Original user query
            subtasks: List of subtasks with dependencies

        Returns:
            TaskExecutionPlan with execution layers
        """
        plan_id = str(uuid.uuid4())
        plan = TaskExecutionPlan(query=query, created_at=time.time())

        # Add all subtasks to plan
        for task in subtasks:
            plan.subtasks[task.id] = task
            plan.total_estimated_duration += task.estimated_duration or 0

        # Build dependency graph
        graph = self._build_dependency_graph(subtasks)

        # Compute execution layers
        execution_layers = self._compute_execution_layers(graph)
        plan.execution_layers = execution_layers

        # Emit plan created event
        self.event_bus.publish_nowait(
            TaskPlanCreatedEvent(
                timestamp=time.time(),
                source="task_orchestrator",
                task_id=plan_id,
                plan_id=plan_id,
                total_subtasks=len(subtasks),
                execution_layers=len(execution_layers),
                estimated_duration=plan.total_estimated_duration,
            )
        )

        self.logger.info(
            "execution_plan_created",
            extra={
                "plan_id": plan_id,
                "subtasks": len(subtasks),
                "layers": len(execution_layers),
            },
        )

        return plan

    def _build_dependency_graph(self, subtasks: list[SubTask]) -> nx.DiGraph:
        """Build a NetworkX DiGraph from subtask dependencies.

        Args:
            subtasks: List of subtasks with dependency relationships

        Returns:
            NetworkX DiGraph representing dependencies
        """
        graph = nx.DiGraph()

        # Add all task nodes
        for task in subtasks:
            graph.add_node(task.id, task=task)

        # Add dependency edges
        for task in subtasks:
            for dep_id in task.dependencies:
                if dep_id in graph.nodes:
                    graph.add_edge(dep_id, task.id)

        return graph

    def _compute_execution_layers(self, graph: nx.DiGraph) -> list[list[str]]:
        """Compute execution layers using topological generations.

        Tasks in the same layer can be executed in parallel.

        Args:
            graph: Dependency graph

        Returns:
            List of layers, each containing independent task IDs
        """
        try:
            generations = list(nx.topological_generations(graph))
            return [list(layer) for layer in generations]
        except nx.NetworkXUnfeasible:
            # Graph has cycles, execute sequentially
            self.logger.warning("cyclic_dependency_graph_fallback_to_sequential")
            return [[node] for node in graph.nodes()]

    async def execute_plan(
        self,
        plan: TaskExecutionPlan,
        agent_map: dict[str, AgentExecutor],
    ) -> dict[str, str]:
        """Execute a task plan with parallel execution.

        Executes tasks layer by layer, with parallel execution
        of independent tasks within each layer.

        Args:
            plan: The execution plan to execute
            agent_map: Mapping of agent_type to executor function

        Returns:
            Dictionary mapping task_id to result
        """
        plan_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        results: dict[str, str] = {}

        plan.status = TaskStatus.in_progress

        try:
            for layer_idx, layer in enumerate(plan.execution_layers):
                # Emit layer started event
                self.event_bus.publish_nowait(
                    TaskLayerStartedEvent(
                        timestamp=time.time(),
                        source="task_orchestrator",
                        plan_id=plan_id,
                        layer_index=layer_idx,
                        layer_count=len(plan.execution_layers),
                        task_count=len(layer),
                    )
                )

                layer_start = time.perf_counter()

                # Execute tasks in this layer in parallel
                layer_results = await self._execute_layer(
                    plan,
                    layer,
                    layer_idx,
                    agent_map,
                    plan_id,
                )

                # Merge results
                results.update(layer_results)

                # Check for failures
                failed_tasks = [
                    tid
                    for tid in layer
                    if plan.subtasks[tid].status == TaskStatus.failed
                ]

                layer_duration = int((time.perf_counter() - layer_start) * 1000)

                # Emit layer completed event
                self.event_bus.publish_nowait(
                    TaskLayerCompletedEvent(
                        timestamp=time.time(),
                        source="task_orchestrator",
                        plan_id=plan_id,
                        layer_index=layer_idx,
                        duration_ms=layer_duration,
                        succeeded_count=len(layer) - len(failed_tasks),
                        failed_count=len(failed_tasks),
                    )
                )

                # Skip dependent tasks if layer failed
                if failed_tasks and self._should_abort_on_failure(plan, layer_idx):
                    self.logger.warning(
                        "aborting_execution_due_to_failures",
                        extra={"failed_tasks": failed_tasks},
                    )
                    break

            # Mark plan as completed
            plan.status = TaskStatus.completed
            total_duration = int((time.perf_counter() - start_time) * 1000)

            # Count final statuses
            completed = plan.completed_subtasks
            failed = plan.failed_subtasks
            skipped = len([t for t in plan.subtasks.values() if t.status == TaskStatus.skipped])

            # Emit plan completed event
            self.event_bus.publish_nowait(
                TaskPlanCompletedEvent(
                    timestamp=time.time(),
                    source="task_orchestrator",
                    task_id=plan_id,
                    plan_id=plan_id,
                    total_tasks=plan.total_subtasks,
                    completed_count=completed,
                    failed_count=failed,
                    skipped_count=skipped,
                    total_duration_ms=total_duration,
                    status=plan.status,
                )
            )

            self.logger.info(
                "execution_plan_completed",
                extra={
                    "plan_id": plan_id,
                    "completed": completed,
                    "failed": failed,
                    "duration_ms": total_duration,
                },
            )

            return results

        except Exception as e:
            self.logger.exception(
                "execution_plan_failed",
                extra={"plan_id": plan_id, "error": str(e)},
            )
            plan.status = TaskStatus.failed
            return results

    async def _execute_layer(
        self,
        plan: TaskExecutionPlan,
        layer: list[str],
        layer_idx: int,
        agent_map: dict[str, AgentExecutor],
        plan_id: str,
    ) -> dict[str, str]:
        """Execute all tasks in a layer in parallel.

        Args:
            plan: The execution plan
            layer: List of task IDs in this layer
            layer_idx: Index of this layer
            agent_map: Mapping of agent_type to executor
            plan_id: Plan ID for events

        Returns:
            Dictionary of task_id to result
        """
        results: dict[str, str] = {}

        # Create tasks for parallel execution
        tasks = []
        for task_id in layer:
            task = plan.subtasks.get(task_id)
            if not task:
                continue
            executor = agent_map.get(task.agent_type)
            if not executor:
                self.logger.warning(
                    "agent_not_found",
                    extra={"agent_type": task.agent_type, "task_id": task_id},
                )
                continue
            tasks.append(self._execute_single_task(task, executor, plan_id, layer_idx))

        # Execute in parallel
        await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for task_id in layer:
            task = plan.subtasks.get(task_id)
            if task and task.result:
                results[task_id] = task.result

        return results

    async def _execute_single_task(
        self,
        task: SubTask,
        executor: AgentExecutor,
        plan_id: str,
        layer_idx: int,
    ) -> None:
        """Execute a single task with error handling and events.

        Args:
            task: The subtask to execute
            executor: The agent executor function
            plan_id: Plan ID for events
            layer_idx: Layer index for events
        """
        task.mark_started()

        # Emit started event
        self.event_bus.publish_nowait(
            TaskStartedEvent(
                timestamp=time.time(),
                source="task_orchestrator",
                task_id=task.id,
                plan_id=plan_id,
                task_title=task.title,
                agent_type=task.agent_type,
                layer=layer_idx,
                total_layers=0,  # Will be set by caller
            )
        )

        start_time = time.perf_counter()

        try:
            # Check if dependencies are satisfied
            deps_satisfied = self._check_dependencies(task, plan_id)
            if not deps_satisfied:
                task.mark_skipped()
                self.event_bus.publish_nowait(
                    TaskSkippedEvent(
                        timestamp=time.time(),
                        source="task_orchestrator",
                        task_id=task.id,
                        plan_id=plan_id,
                        task_title=task.title,
                        reason="Dependencies not satisfied",
                    )
                )
                return

            # Execute the task
            result = await self._call_agent(executor, task)

            # Mark completed
            task.mark_completed(result)

            duration = int((time.perf_counter() - start_time) * 1000)

            self.event_bus.publish_nowait(
                TaskCompletedEvent(
                    timestamp=time.time(),
                    source="task_orchestrator",
                    task_id=task.id,
                    plan_id=plan_id,
                    task_title=task.title,
                    agent_type=task.agent_type,
                    duration_ms=duration,
                    result_length=len(result) if result else 0,
                )
            )

            self.logger.info(
                "task_completed",
                extra={
                    "task_id": task.id,
                    "agent_type": task.agent_type,
                    "duration_ms": duration,
                },
            )

        except Exception as e:
            duration = int((time.perf_counter() - start_time) * 1000)
            error_msg = str(e)

            task.mark_failed(error_msg)

            self.event_bus.publish_nowait(
                TaskFailedEvent(
                    timestamp=time.time(),
                    source="task_orchestrator",
                    task_id=task.id,
                    plan_id=plan_id,
                    task_title=task.title,
                    agent_type=task.agent_type,
                    error=error_msg,
                    duration_ms=duration,
                )
            )

            self.logger.warning(
                "task_failed",
                extra={
                    "task_id": task.id,
                    "agent_type": task.agent_type,
                    "error": error_msg,
                },
            )

    def _check_dependencies(self, task: SubTask, plan_id: str) -> bool:
        """Check if task dependencies are satisfied.

        Args:
            task: The subtask to check
            plan_id: Plan ID (for future use in tracking)

        Returns:
            True if all dependencies are completed
        """
        # This is a placeholder - in real implementation, we'd track
        # the plan state to check actual dependency status
        return True

    async def _call_agent(
        self, executor: AgentExecutor, task: SubTask
    ) -> str | None:
        """Call the agent executor with the task.

        Args:
            executor: The agent executor function
            task: The subtask with query and context

        Returns:
            Result string from the agent
        """
        import asyncio

        # Handle both sync and async executors
        result = executor(task.description, task.agent_type, task.context)

        if asyncio.iscoroutine(result):
            return await result
        return result

    def _should_abort_on_failure(self, plan: TaskExecutionPlan, layer_idx: int) -> bool:
        """Decide whether to abort execution on layer failure.

        Currently, we continue execution even if some tasks fail.
        This can be configured in the future.

        Args:
            plan: The execution plan
            layer_idx: Index of the failed layer

        Returns:
            True if execution should abort
        """
        # Continue execution for now
        return False

    def get_progress(self, plan: TaskExecutionPlan) -> TaskProgress:
        """Get current execution progress.

        Args:
            plan: The execution plan

        Returns:
            TaskProgress with current status
        """
        return TaskProgress(
            plan_id=str(uuid.uuid4()),
            completed_count=plan.completed_subtasks,
            total_count=plan.total_subtasks,
            current_layer=0,
            total_layers=len(plan.execution_layers),
        )


# Global instance factory
_orchestrator_instance: TaskOrchestrator | None = None


def get_task_orchestrator(
    event_bus: EventBus | None = None,
) -> TaskOrchestrator:
    """Get or create the global TaskOrchestrator instance.

    Args:
        event_bus: Optional EventBus (uses global if not provided)

    Returns:
        TaskOrchestrator instance
    """
    global _orchestrator_instance

    if _orchestrator_instance is None:
        if event_bus is None:
            from aiops.core.events import get_event_bus
            event_bus = get_event_bus()

        _orchestrator_instance = TaskOrchestrator(event_bus=event_bus)

    return _orchestrator_instance
