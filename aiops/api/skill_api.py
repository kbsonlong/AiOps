from __future__ import annotations

from fastapi import FastAPI, Query

from aiops.skills import SkillCategory, SkillDiscoveryService, SkillRegistry
from aiops.skills_lib import (
    FAULT_DIAGNOSIS_SKILLS,
    PROMETHEUS_SKILLS,
    SECURITY_SKILLS,
    VICTORIALOGS_SKILLS,
)

app = FastAPI(title="AIOps Skill API")


def build_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.bulk_register(PROMETHEUS_SKILLS)
    registry.bulk_register(VICTORIALOGS_SKILLS)
    registry.bulk_register(FAULT_DIAGNOSIS_SKILLS)
    registry.bulk_register(SECURITY_SKILLS)
    return registry


@app.get("/skills")
def list_skills():
    registry = build_registry()
    return [skill.model_dump() for skill in registry.all()]


@app.get("/skills/discover")
def discover_skills(
    query: str,
    category: SkillCategory | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
):
    registry = build_registry()
    discovery = SkillDiscoveryService(registry=registry)
    results = discovery.discover_skills(query, category=category, tags=tag)
    return [skill.model_dump() for skill in results]
