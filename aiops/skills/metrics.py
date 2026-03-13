from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class SkillMetrics:
    executions: int = 0
    successes: int = 0
    failures: int = 0
    avg_execution_time: float = 0.0

    def record(self, success: bool, execution_time: float) -> None:
        self.executions += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        if self.executions == 1:
            self.avg_execution_time = execution_time
        else:
            self.avg_execution_time = (
                (self.avg_execution_time * (self.executions - 1)) + execution_time
            ) / self.executions

    def to_dict(self) -> Dict[str, float]:
        success_rate = (self.successes / self.executions) if self.executions else 0.0
        return {
            "executions": float(self.executions),
            "successes": float(self.successes),
            "failures": float(self.failures),
            "avg_execution_time": self.avg_execution_time,
            "success_rate": success_rate,
        }
