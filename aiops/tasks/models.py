"""Task data models for decomposition and orchestration.

This module defines the core data structures used throughout the task
decomposition and orchestration system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task in the execution lifecycle."""

    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class TaskPriority(str, Enum):
    """Priority levels for task execution scheduling."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SubTask(BaseModel):
    """A single atomic task within a larger execution plan.

    Attributes:
        id: Unique identifier for this subtask (e.g., "task_1")
        title: Human-readable title describing what this task does
        description: Detailed description of the task purpose
        agent_type: The type of agent that should handle this task
        status: Current execution status
        priority: Execution priority for scheduling
        dependencies: List of task IDs that must complete before this one
        estimated_duration: Estimated execution time in seconds
        context: Additional contextual data for execution
        result: Output result upon completion
        error: Error message if task failed
        started_at: Unix timestamp when execution started
        completed_at: Unix timestamp when execution completed
    """

    id: str
    title: str
    description: str
    agent_type: str
    status: TaskStatus = TaskStatus.pending
    priority: TaskPriority = TaskPriority.medium
    dependencies: list[str] = Field(default_factory=list)
    estimated_duration: Optional[int] = None
    context: dict[str, Any] = Field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def mark_started(self) -> None:
        """Mark task as in progress and record start time."""
        self.status = TaskStatus.in_progress
        self.started_at = time.time()

    def mark_completed(self, result: str | None = None) -> None:
        """Mark task as completed with optional result."""
        self.status = TaskStatus.completed
        self.completed_at = time.time()
        if result is not None:
            self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark task as failed with error message."""
        self.status = TaskStatus.failed
        self.completed_at = time.time()
        self.error = error

    def mark_skipped(self) -> None:
        """Mark task as skipped (e.g., due to failed dependency)."""
        self.status = TaskStatus.skipped
        self.completed_at = time.time()

    @property
    def duration_ms(self) -> int | None:
        """Calculate actual execution duration in milliseconds."""
        if self.started_at is not None and self.completed_at is not None:
            return int((self.completed_at - self.started_at) * 1000)
        return None


class TaskExecutionPlan(BaseModel):
    """A complete execution plan for decomposed tasks.

    Contains all subtasks with their dependency relationships and
    the computed execution order for parallel processing.

    Attributes:
        query: Original user query that triggered this plan
        subtasks: Dictionary of all subtasks keyed by ID
        execution_layers: List of layers, each containing independent task IDs
        total_estimated_duration: Sum of all task durations (optimistic)
        created_at: Unix timestamp when plan was created
        status: Overall plan status
    """

    query: str
    subtasks: dict[str, SubTask] = Field(default_factory=dict)
    execution_layers: list[list[str]] = Field(default_factory=list)
    total_estimated_duration: int = 0
    created_at: float = Field(default_factory=time.time)
    status: TaskStatus = TaskStatus.pending

    @property
    def total_subtasks(self) -> int:
        """Total number of subtasks in the plan."""
        return len(self.subtasks)

    @property
    def completed_subtasks(self) -> int:
        """Number of completed subtasks."""
        return sum(1 for t in self.subtasks.values() if t.status == TaskStatus.completed)

    @property
    def failed_subtasks(self) -> int:
        """Number of failed subtasks."""
        return sum(1 for t in self.subtasks.values() if t.status == TaskStatus.failed)

    @property
    def progress_percent(self) -> float:
        """Completion percentage (0-100)."""
        if self.total_subtasks == 0:
            return 100.0
        return (self.completed_subtasks / self.total_subtasks) * 100

    def get_subtask(self, task_id: str) -> SubTask | None:
        """Get a subtask by ID."""
        return self.subtasks.get(task_id)

    def get_ready_tasks(self) -> list[SubTask]:
        """Get tasks whose dependencies are all satisfied and are pending."""
        ready = []
        for task in self.subtasks.values():
            if task.status != TaskStatus.pending:
                continue
            deps_satisfied = all(
                self.subtasks.get(dep_id, SubTask(id="", title="", description="", agent_type="")).status
                == TaskStatus.completed
                for dep_id in task.dependencies
            )
            if deps_satisfied:
                ready.append(task)
        return ready

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the execution plan."""
        return {
            "query": self.query,
            "total_subtasks": self.total_subtasks,
            "completed": self.completed_subtasks,
            "failed": self.failed_subtasks,
            "progress": f"{self.progress_percent:.1f}%",
            "status": self.status.value,
            "estimated_duration": self.total_estimated_duration,
        }


class TaskDecompositionResult(BaseModel):
    """Result of task decomposition analysis.

    Contains the decision of whether to decompose and the
    resulting execution plan if decomposition was performed.

    Attributes:
        should_decompose: Whether the query was complex enough to decompose
        complexity_score: Computed complexity score (0-1)
        subtasks: List of decomposed subtasks (empty if no decomposition)
        reasoning: Explanation of the decomposition decision
        execution_plan: Complete execution plan (created after orchestration)
    """

    should_decompose: bool
    complexity_score: float = Field(ge=0.0, le=1.0)
    subtasks: list[SubTask] = Field(default_factory=list)
    reasoning: str = ""
    execution_plan: Optional[TaskExecutionPlan] = None

    @property
    def subtask_count(self) -> int:
        """Number of subtasks in the decomposition."""
        return len(self.subtasks)


@dataclass(slots=True)
class TaskProgress:
    """Real-time progress tracking for task execution.

    Used for streaming progress updates to clients.
    """

    plan_id: str
    current_task_id: str | None = None
    completed_count: int = 0
    total_count: int = 0
    current_layer: int = 0
    total_layers: int = 0
    errors: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "plan_id": self.plan_id,
            "current_task_id": self.current_task_id,
            "completed_count": self.completed_count,
            "total_count": self.total_count,
            "current_layer": self.current_layer,
            "total_layers": self.total_layers,
            "progress_percent": (self.completed_count / self.total_count * 100) if self.total_count > 0 else 0,
            "errors": self.errors or [],
        }
