from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class SkillPermissionChecker:
    """Simple permission checker for skill management."""

    allow_create: bool = True
    allow_scan: bool = True
    allow_quality: bool = True
    allow_list: bool = True

    def ensure_allowed(self, action: str, user: Optional[str] = None) -> None:
        allowed = {
            "create": self.allow_create,
            "scan": self.allow_scan,
            "quality": self.allow_quality,
            "list": self.allow_list,
        }.get(action, False)
        if not allowed:
            raise PermissionError(f"Skill action '{action}' is not allowed")
