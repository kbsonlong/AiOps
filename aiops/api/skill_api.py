from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from aiops.auth import SkillPermissionChecker
from aiops.config import load_settings
from aiops.config.validator import validate_settings
from aiops.core.error_handler import get_logger, safe_execute, to_safe_message
from aiops.exceptions import ConfigException
from aiops.health import build_health_report
from aiops.skills import SkillCategory, SkillDiscoveryService, SkillRegistry
from aiops.skills.global_registry import get_global_skill_registry
from aiops.skills.exceptions import SecurityBlockedError, SkillExistsError, SkillQualityError, ValidationError
from aiops.skills.manager import SkillManager


def _skill_safe_detail(exc: BaseException) -> str:
    if isinstance(exc, SkillExistsError):
        return "技能已存在"
    if isinstance(exc, SkillQualityError):
        return "技能质量不达标"
    if isinstance(exc, SecurityBlockedError):
        return "技能未通过安全检查"
    if isinstance(exc, ValidationError):
        return "请求参数或技能内容不合法"
    return to_safe_message(exc)


def _raise_http_error(exc: BaseException, *, status_code: int, detail: str) -> None:
    raise HTTPException(status_code=status_code, detail=detail) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    result = validate_settings(settings)
    if not result.valid:
        raise ConfigException(result.to_message(), safe_message="配置校验失败")
    yield


app = FastAPI(title="AIOps Skill API", lifespan=lifespan)
permission_checker = SkillPermissionChecker()


def build_registry() -> SkillRegistry:
    return get_global_skill_registry()


@app.get("/health")
def health():
    return build_health_report()


@app.get("/ready")
def ready():
    report = build_health_report()
    if report.get("status") != "healthy":
        return JSONResponse(status_code=503, content=report)
    return report


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
    def _run():
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

    def _on_error(exc: BaseException):
        if isinstance(exc, (SkillQualityError, SecurityBlockedError, SkillExistsError, ValidationError)):
            _raise_http_error(exc, status_code=400, detail=_skill_safe_detail(exc))
        if isinstance(exc, PermissionError):
            _raise_http_error(exc, status_code=403, detail=to_safe_message(exc))
        _raise_http_error(exc, status_code=500, detail=to_safe_message(exc))

    return safe_execute(_run, operation="api.skills.create", on_error=_on_error, logger=get_logger())


@app.get("/skills/user")
def list_user_skills():
    def _run():
        permission_checker.ensure_allowed("list")
        manager = SkillManager()
        return manager.list_user_skills()

    def _on_error(exc: BaseException):
        if isinstance(exc, PermissionError):
            _raise_http_error(exc, status_code=403, detail=to_safe_message(exc))
        _raise_http_error(exc, status_code=500, detail=to_safe_message(exc))

    return safe_execute(_run, operation="api.skills.user.list", on_error=_on_error, logger=get_logger())


@app.post("/skills/{skill_id}/scan")
def rescan_skill(skill_id: str):
    def _run():
        permission_checker.ensure_allowed("scan")
        manager = SkillManager()
        result = manager.scan_skill(skill_id)
        return result.model_dump()

    def _on_error(exc: BaseException):
        if isinstance(exc, ValidationError):
            _raise_http_error(exc, status_code=404, detail="技能不存在")
        if isinstance(exc, PermissionError):
            _raise_http_error(exc, status_code=403, detail=to_safe_message(exc))
        _raise_http_error(exc, status_code=500, detail=to_safe_message(exc))

    return safe_execute(_run, operation="api.skills.scan", on_error=_on_error, logger=get_logger())


@app.get("/skills/{skill_id}/quality")
def quality_report(skill_id: str):
    def _run():
        permission_checker.ensure_allowed("quality")
        manager = SkillManager()
        score = manager.evaluate_quality(skill_id)
        return score.model_dump()

    def _on_error(exc: BaseException):
        if isinstance(exc, ValidationError):
            _raise_http_error(exc, status_code=404, detail="技能不存在")
        if isinstance(exc, PermissionError):
            _raise_http_error(exc, status_code=403, detail=to_safe_message(exc))
        _raise_http_error(exc, status_code=500, detail=to_safe_message(exc))

    return safe_execute(_run, operation="api.skills.quality", on_error=_on_error, logger=get_logger())
