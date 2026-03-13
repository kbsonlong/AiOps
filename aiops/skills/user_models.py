from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from aiops.skills.models import SkillCategory, SkillDefinition, SkillRiskLevel


class QualityScore(BaseModel):
    overall: float
    category_scores: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)


class ScanResult(BaseModel):
    risk_level: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class UserSkillMetadata(BaseModel):
    """User skill metadata stored on disk."""

    skill_id: str
    file_path: Path
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    quality_score: Optional[QualityScore] = None
    security_scan: Optional[ScanResult] = None
    execution_stats: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)


class UserSkill:
    """User skill composed of an existing SkillDefinition and disk metadata."""

    def __init__(self, skill_id: str, definition: SkillDefinition, metadata: UserSkillMetadata):
        self.skill_id = skill_id
        self.definition = definition
        self.metadata = metadata

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def category(self) -> SkillCategory:
        return self.definition.category

    @property
    def risk_level(self) -> SkillRiskLevel:
        if self.metadata.security_scan and self.metadata.security_scan.risk_level == "dangerous":
            return SkillRiskLevel.CRITICAL
        return self.definition.risk_level

    def to_dict(self) -> Dict[str, Any]:
        base = self.definition.model_dump()
        base.update(
            {
                "skill_type": "user_created",
                "file_path": str(self.metadata.file_path),
                "created_by": self.metadata.created_by,
                "created_at": self.metadata.created_at.isoformat(),
                "updated_at": self.metadata.updated_at.isoformat(),
                "quality_score": self.metadata.quality_score.model_dump()
                if self.metadata.quality_score
                else None,
                "security_scan": self.metadata.security_scan.model_dump()
                if self.metadata.security_scan
                else None,
            }
        )
        return base
