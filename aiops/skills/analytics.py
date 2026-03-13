from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from aiops.skills.metrics import SkillMetrics


@dataclass(slots=True)
class SkillAnalytics:
    metrics: Dict[str, SkillMetrics]

    def top_skills(self, limit: int = 5) -> List[str]:
        ranked = sorted(self.metrics.items(), key=lambda item: item[1].executions, reverse=True)
        return [skill_id for skill_id, _ in ranked[:limit]]
