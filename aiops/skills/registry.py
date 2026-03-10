from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from aiops.skills.models import SkillDefinition


@dataclass(slots=True)
class SkillRegistry:
    skills: Dict[str, SkillDefinition] = field(default_factory=dict)

    def register(self, skill: SkillDefinition) -> None:
        self.skills[skill.id] = skill

    def bulk_register(self, skills: Iterable[SkillDefinition]) -> None:
        for skill in skills:
            self.register(skill)

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        return self.skills.get(skill_id)

    def all(self) -> List[SkillDefinition]:
        return list(self.skills.values())
