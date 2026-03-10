from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    MONITORING = "monitoring"
    DIAGNOSIS = "diagnosis"
    REMEDIATION = "remediation"
    SECURITY = "security"
    REPORTING = "reporting"
    CUSTOM = "custom"


class SkillRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SkillRequirement(BaseModel):
    """Skill execution requirements."""

    python_version: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    resources: Dict[str, Any] = Field(default_factory=dict)


class SkillDefinition(BaseModel):
    """Skill definition model."""

    id: str
    name: str
    description: str
    version: str = "1.0.0"

    category: SkillCategory
    subcategory: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: SkillRiskLevel = SkillRiskLevel.LOW

    implementation_type: str
    implementation_ref: str

    author: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    requirements: SkillRequirement = Field(default_factory=SkillRequirement)
    avg_execution_time: Optional[float] = None
    success_rate: Optional[float] = None
