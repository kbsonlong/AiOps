from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from aiops.skills.models import SkillCategory, SkillDefinition
from aiops.skills.registry import SkillRegistry


@dataclass(slots=True)
class SkillDiscoveryService:
    registry: SkillRegistry

    def discover_skills(
        self,
        query: str,
        category: Optional[SkillCategory] = None,
        tags: Optional[List[str]] = None,
    ) -> List[SkillDefinition]:
        query_l = query.lower()
        tag_set = set(t.lower() for t in (tags or []))
        results: list[SkillDefinition] = []
        for skill in self.registry.all():
            if category and skill.category != category:
                continue
            tag_match = not tag_set or tag_set.intersection({t.lower() for t in skill.tags})
            if tag_set and not tag_match:
                continue
            haystack = " ".join([skill.name, skill.description, " ".join(skill.tags)]).lower()
            query_match = not query_l or query_l in haystack
            if tag_set:
                if query_match or tag_match:
                    results.append(skill)
            elif query_match:
                results.append(skill)
        return results

    def recommend_skills(self, problem_description: str) -> List[SkillDefinition]:
        keywords = problem_description.lower().split()
        candidates: list[SkillDefinition] = []
        for skill in self.registry.all():
            haystack = " ".join([skill.name, skill.description, " ".join(skill.tags)]).lower()
            if any(word in haystack for word in keywords):
                candidates.append(skill)
        return candidates
