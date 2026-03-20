"""Task-specific event types for progress tracking.

This module defines events that are emitted during task decomposition
and execution for observability and monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass

from aiops.core.events import Event
from aiops.tasks.models import TaskStatus


@dataclass(slots=True)
class TaskEvent(Event):
    """Base event for all task-related events.

    Attributes:
        timestamp: Unix timestamp when the event occurred
        source: Source of the event (e.g., "task_orchestrator")
        task_id: Unique identifier of the task
        plan_id: Unique identifier of the execution plan
    """

    task_id: str
    plan_id: str


@dataclass(slots=True)
class TaskDecompositionStartedEvent(TaskEvent):
    """Emitted when task decomposition begins."""

    query: str


@dataclass(slots=True)
class TaskDecompositionCompletedEvent(TaskEvent):
    """Emitted when task decomposition completes.

    Attributes:
        subtask_count: Number of subtasks created
        complexity_score: Complexity score (0-1)
        duration_ms: Time taken for decomposition in milliseconds
    """

    subtask_count: int
    complexity_score: float
    duration_ms: int


@dataclass(slots=True)
class TaskPlanCreatedEvent(TaskEvent):
    """Emitted when an execution plan is created.

    Attributes:
        total_subtasks: Total number of subtasks in the plan
        execution_layers: Number of execution layers (parallel groups)
        estimated_duration: Estimated total duration in seconds
    """

    total_subtasks: int
    execution_layers: int
    estimated_duration: int


@dataclass(slots=True)
class TaskStartedEvent(TaskEvent):
    """Emitted when a subtask starts execution.

    Attributes:
        task_title: Human-readable title of the task
        agent_type: Type of agent handling this task
        layer: Execution layer this task belongs to
        total_layers: Total number of execution layers
    """

    task_title: str
    agent_type: str
    layer: int
    total_layers: int


@dataclass(slots=True)
class TaskCompletedEvent(TaskEvent):
    """Emitted when a subtask completes successfully.

    Attributes:
        task_title: Human-readable title of the task
        agent_type: Type of agent that handled this task
        duration_ms: Actual execution duration in milliseconds
        result_length: Length of the result string (for logging)
    """

    task_title: str
    agent_type: str
    duration_ms: int
    result_length: int


@dataclass(slots=True)
class TaskFailedEvent(TaskEvent):
    """Emitted when a subtask fails.

    Attributes:
        task_title: Human-readable title of the task
        agent_type: Type of agent that was handling this task
        error: Error message describing the failure
        duration_ms: Time before failure in milliseconds
    """

    task_title: str
    agent_type: str
    error: str
    duration_ms: int


@dataclass(slots=True)
class TaskSkippedEvent(TaskEvent):
    """Emitted when a subtask is skipped.

    This typically happens when a dependency fails.

    Attributes:
        task_title: Human-readable title of the task
        reason: Explanation of why the task was skipped
    """

    task_title: str
    reason: str


@dataclass(slots=True)
class TaskLayerStartedEvent(Event):
    """Emitted when an execution layer starts.

    Attributes:
        plan_id: Execution plan identifier
        layer_index: Zero-based index of the layer
        layer_count: Total number of layers
        task_count: Number of tasks in this layer
    """

    plan_id: str
    layer_index: int
    layer_count: int
    task_count: int


@dataclass(slots=True)
class TaskLayerCompletedEvent(Event):
    """Emitted when an execution layer completes.

    Attributes:
        plan_id: Execution plan identifier
        layer_index: Zero-based index of the completed layer
        duration_ms: Time taken for this layer in milliseconds
        succeeded_count: Number of tasks that succeeded
        failed_count: Number of tasks that failed
    """

    plan_id: str
    layer_index: int
    duration_ms: int
    succeeded_count: int
    failed_count: int


@dataclass(slots=True)
class TaskPlanCompletedEvent(TaskEvent):
    """Emitted when the entire execution plan completes.

    Attributes:
        total_tasks: Total number of tasks in the plan
        completed_count: Number of tasks that completed successfully
        failed_count: Number of tasks that failed
        skipped_count: Number of tasks that were skipped
        total_duration_ms: Total execution time in milliseconds
        status: Final status of the plan
    """

    total_tasks: int
    completed_count: int
    failed_count: int
    skipped_count: int
    total_duration_ms: int
    status: TaskStatus
