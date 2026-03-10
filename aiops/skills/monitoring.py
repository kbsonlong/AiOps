from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from aiops.skills.runtime import SkillExecutionResult


@dataclass(slots=True)
class SkillExecutionMonitor:
    history: List[SkillExecutionResult] = field(default_factory=list)

    def record(self, result: SkillExecutionResult) -> None:
        self.history.append(result)

    def success_rate(self) -> float:
        if not self.history:
            return 0.0
        success = sum(1 for item in self.history if item.success)
        return success / len(self.history)

    def stats(self) -> Dict[str, float]:
        if not self.history:
            return {"count": 0.0, "avg_execution_time": 0.0}
        avg = sum(item.execution_time for item in self.history) / len(self.history)
        return {"count": float(len(self.history)), "avg_execution_time": avg}
