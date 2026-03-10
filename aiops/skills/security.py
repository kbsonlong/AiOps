from __future__ import annotations

from aiops.config.security_config import SecurityConfig
from aiops.security.controller import SecurityController
from aiops.skills.models import SkillRiskLevel


def build_skill_security_controller() -> SecurityController:
    config = SecurityConfig(
        approval_required=True,
        allowed_actions=[
            "prometheus.query.cpu",
            "prometheus.query.memory",
            "victorialogs.query.logs",
            "diagnose.root.cause",
            "recommend.solution",
        ],
    )
    return SecurityController(config=config)


def requires_approval(risk_level: SkillRiskLevel) -> bool:
    return risk_level in (SkillRiskLevel.HIGH, SkillRiskLevel.CRITICAL)
