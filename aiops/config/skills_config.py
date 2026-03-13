from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class SkillsConfig(BaseModel):
    """Configuration for user skills storage and controls."""

    base_dir: str = Field(default="~/.aiops")
    quality_threshold: float = Field(default=0.7)
    scan_enabled: bool = Field(default=True)
    auto_register: bool = Field(default=True)
    max_size_mb: int = Field(default=10)
    allowed_categories: List[str] = Field(
        default_factory=lambda: [
            "monitoring",
            "diagnosis",
            "remediation",
            "security",
            "reporting",
            "custom",
        ]
    )

    @field_validator("allowed_categories", mode="before")
    @classmethod
    def _split_allowed_categories(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value
