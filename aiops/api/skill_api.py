from __future__ import annotations

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field

from aiops.auth import SkillPermissionChecker
from aiops.skills import SkillCategory, SkillDiscoveryService, SkillRegistry
from aiops.skills.exceptions import SecurityBlockedError, SkillExistsError, SkillQualityError, ValidationError
from aiops.skills.manager import SkillManager
from aiops.skills_lib import (
    FAULT_DIAGNOSIS_SKILLS,
    PROMETHEUS_SKILLS,
    SECURITY_SKILLS,
    VICTORIALOGS_SKILLS,
)

app = FastAPI(title="AIOps Skill API")
permission_checker = SkillPermissionChecker()


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


class SkillCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    category: str = Field(default="custom")
    description: str = Field(default="")
    author: str | None = None
    risk_level: str = Field(default="medium")
    tags: list[str] = Field(default_factory=list)


@app.post("/skills/create")
def create_skill(req: SkillCreateRequest):
    try:
        permission_checker.ensure_allowed("create")
        manager = SkillManager()
        user_skill = manager.create_skill(
            name=req.name,
            content=req.content,
            category=req.category,
            metadata={
                "description": req.description,
                "author": req.author,
                "risk_level": req.risk_level,
                "tags": req.tags,
            },
        )
        return user_skill.to_dict()
    except (SkillQualityError, SecurityBlockedError, SkillExistsError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/skills/user")
def list_user_skills():
    try:
        permission_checker.ensure_allowed("list")
        manager = SkillManager()
        return manager.list_user_skills()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/skills/{skill_id}/scan")
def rescan_skill(skill_id: str):
    try:
        permission_checker.ensure_allowed("scan")
        manager = SkillManager()
        result = manager.scan_skill(skill_id)
        return result.model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/skills/{skill_id}/quality")
def quality_report(skill_id: str):
    try:
        permission_checker.ensure_allowed("quality")
        manager = SkillManager()
        score = manager.evaluate_quality(skill_id)
        return score.model_dump()
    except ValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
