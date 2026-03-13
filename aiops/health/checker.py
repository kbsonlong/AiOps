from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from aiops.config import load_settings
from aiops.config.validator import validate_settings


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str = ""
    issues: list[str] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_health_report(
) -> dict:
    settings = load_settings()
    result = validate_settings(settings)
    status = "healthy" if result.valid else "unhealthy"
    issues = [f"{issue.path}: {issue.message}" for issue in result.issues]
    checks: dict[str, CheckResult] = {
        "config": CheckResult(
            name="config",
            status=status,
            issues=issues,
        )
    }
    return {
        "status": status,
        "timestamp": _now_iso(),
        "checks": {name: check.__dict__ for name, check in checks.items()},
    }
