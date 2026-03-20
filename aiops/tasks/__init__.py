"""Task decomposition and orchestration system.

This package provides intelligent task decomposition and orchestration
capabilities for the AIOps system, enabling multi-agent collaboration
with dependency-aware execution.

Example:
    >>> from aiops.tasks import get_task_decomposer, get_task_orchestrator
    >>> decomposer = get_task_decomposer()
    >>> result = await decomposer.decompose(state)
    >>> orchestrator = get_task_orchestrator()
    >>> plan = orchestrator.build_execution_plan(query, result.subtasks)
"""

from __future__ import annotations

from aiops.tasks.decomposer import (
    DecompositionSchema,
    SubTaskDefinition,
    TaskDecomposer,
    get_task_decomposer,
)
from aiops.tasks.events import (
    TaskCompletedEvent,
    TaskDecompositionCompletedEvent,
    TaskDecompositionStartedEvent,
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
    TaskDecompositionResult,
    TaskExecutionPlan,
    TaskPriority,
    TaskProgress,
    TaskStatus,
)
from aiops.tasks.orchestrator import (
    AgentExecutor,
    TaskOrchestrator,
    get_task_orchestrator,
)

__all__ = [
    # Models
    "SubTask",
    "TaskExecutionPlan",
    "TaskDecompositionResult",
    "TaskStatus",
    "TaskPriority",
    "TaskProgress",
    # Decomposer
    "TaskDecomposer",
    "DecompositionSchema",
    "SubTaskDefinition",
    "get_task_decomposer",
    # Orchestrator
    "TaskOrchestrator",
    "AgentExecutor",
    "get_task_orchestrator",
    # Events
    "TaskEvent",
    "TaskStartedEvent",
    "TaskCompletedEvent",
    "TaskFailedEvent",
    "TaskSkippedEvent",
    "TaskDecompositionStartedEvent",
    "TaskDecompositionCompletedEvent",
    "TaskPlanCreatedEvent",
    "TaskLayerStartedEvent",
    "TaskLayerCompletedEvent",
    "TaskPlanCompletedEvent",
]
