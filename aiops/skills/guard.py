from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from aiops.skills.security_patterns import AIOPS_SPECIFIC_PATTERNS, BASE_PATTERNS, WHITELIST_PATTERNS
from aiops.skills.user_models import ScanResult


class SkillsGuard:
    """Skill security scanner with AIOps-specific rules."""

    def __init__(self) -> None:
        self.patterns = BASE_PATTERNS + AIOPS_SPECIFIC_PATTERNS
        self.whitelist_patterns = WHITELIST_PATTERNS

    def scan_skill(self, skill_dir: Path) -> ScanResult:
        results: List[Dict[str, Any]] = []
        for file_path in skill_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in [".md", ".py", ".sh", ".yaml", ".yml"]:
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if self._is_whitelisted(content):
                continue
            for pattern, level, desc in self.patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    results.append(
                        {
                            "file": str(file_path.relative_to(skill_dir)),
                            "level": level,
                            "description": desc,
                            "pattern": pattern,
                            "context": self._extract_context(content, pattern),
                        }
                    )
        return self._calculate_risk_level(results)

    def _is_whitelisted(self, content: str) -> bool:
        return any(re.search(p, content, re.IGNORECASE) for p in self.whitelist_patterns)

    def _extract_context(self, content: str, pattern: str, window: int = 60) -> str:
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            return ""
        start = max(match.start() - window, 0)
        end = min(match.end() + window, len(content))
        return content[start:end].replace("\n", " ")

    def _calculate_risk_level(self, results: List[Dict[str, Any]]) -> ScanResult:
        if any(item["level"] == "dangerous" for item in results):
            risk = "dangerous"
        elif any(item["level"] == "caution" for item in results):
            risk = "caution"
        else:
            risk = "safe"
        summary = f"{len(results)} issues detected" if results else "No issues detected"
        return ScanResult(risk_level=risk, issues=results, summary=summary)
