from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from aiops.config.settings import load_settings
from aiops.skills.exceptions import (
    SecurityBlockedError,
    SkillExistsError,
    SkillQualityError,
    ValidationError,
)
from aiops.skills.guard import SkillsGuard
from aiops.skills.models import SkillCategory, SkillDefinition, SkillRiskLevel
from aiops.skills.quality import SkillQualityEvaluator
from aiops.skills.storage import VALID_SKILL_ID_PATTERN, init_storage, slugify
from aiops.skills.user_models import ScanResult, UserSkill, UserSkillMetadata


class SkillManager:
    """Skill management for dynamic creation."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.storage = init_storage(base_dir)
        self.quality_evaluator = SkillQualityEvaluator()
        self.security_guard = SkillsGuard()
        self.settings = load_settings()

    def create_skill(
        self,
        name: str,
        content: str,
        category: str,
        metadata: Dict[str, Any],
    ) -> UserSkill:
        category_slug = slugify(category)
        skill_id = f"{category_slug}-{slugify(name)}"
        skill_dir = self.storage.skills_dir / skill_id

        self._validate_new_skill(skill_id, skill_dir, category_slug)

        full_content = self._build_skill_content(name, content, category_slug, metadata)

        quality_score = self.quality_evaluator.evaluate(full_content)
        if quality_score.overall < self.settings.skills.quality_threshold:
            raise SkillQualityError(
                f"技能质量评分不足: {quality_score.overall:.2f}。建议: {', '.join(quality_score.recommendations)}"
            )

        skill_dir.mkdir(parents=True, exist_ok=False)
        self._atomic_write(skill_dir / "SKILL.md", full_content)

        scan_result = ScanResult(risk_level="safe", issues=[], summary="Scan disabled")
        if self.settings.skills.scan_enabled:
            scan_result = self.security_guard.scan_skill(skill_dir)
            if scan_result.risk_level == "dangerous":
                shutil.rmtree(skill_dir)
                raise SecurityBlockedError(f"技能包含危险内容: {scan_result.summary}")

        skill_def = self._create_skill_definition(skill_id, name, category_slug, metadata, skill_dir)
        user_skill = UserSkill(
            skill_id=skill_id,
            definition=skill_def,
            metadata=UserSkillMetadata(
                skill_id=skill_id,
                file_path=skill_dir / "SKILL.md",
                created_by=metadata.get("author", "unknown"),
                quality_score=quality_score,
                security_scan=scan_result,
                tags=metadata.get("tags", []),
            ),
        )

        self._update_skill_index(user_skill)
        self._record_version(user_skill, metadata, full_content)
        return user_skill

    def _validate_new_skill(self, skill_id: str, skill_dir: Path, category: str) -> None:
        if skill_dir.exists():
            raise SkillExistsError(f"技能已存在: {skill_id}")
        if not VALID_SKILL_ID_PATTERN.match(skill_id):
            raise ValidationError(f"技能ID格式无效: {skill_id}")
        if category not in self.settings.skills.allowed_categories:
            raise ValidationError(f"技能类别不允许: {category}")

    def _build_skill_content(
        self, name: str, content: str, category: str, metadata: Dict[str, Any]
    ) -> str:
        frontmatter = {
            "name": name,
            "description": metadata.get("description", ""),
            "category": category,
            "version": "1.0.0",
            "author": metadata.get("author", "AIOps Agent"),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "risk_level": metadata.get("risk_level", "medium"),
            "tags": metadata.get("tags", []),
        }
        yaml_content = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
        return f"---\n{yaml_content}---\n\n{content}"

    def _atomic_write(self, target: Path, content: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=str(target.parent)) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        temp_path.replace(target)

    def _create_skill_definition(
        self,
        skill_id: str,
        name: str,
        category: str,
        metadata: Dict[str, Any],
        skill_dir: Path,
    ) -> SkillDefinition:
        try:
            category_enum = SkillCategory(category)
        except ValueError:
            category_enum = SkillCategory.CUSTOM
        risk = metadata.get("risk_level", "medium").lower()
        risk_level = SkillRiskLevel.MEDIUM
        if risk in {"low", "medium", "high", "critical"}:
            risk_level = SkillRiskLevel(risk)
        return SkillDefinition(
            id=skill_id,
            name=name,
            description=metadata.get("description", ""),
            category=category_enum,
            tags=metadata.get("tags", []),
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            risk_level=risk_level,
            implementation_type="user_skill",
            implementation_ref=str(skill_dir / "SKILL.md"),
            author=metadata.get("author"),
        )

    def _update_skill_index(self, user_skill: UserSkill) -> None:
        index_file = self.storage.index_file
        current = self._load_index()
        current = [item for item in current if item.get("skill_id") != user_skill.skill_id]
        current.append(self._index_entry(user_skill))
        self._write_index(current)
    
    def _record_version(self, user_skill: UserSkill, metadata: Dict[str, Any], content: str) -> None:
        from hashlib import sha256

        from aiops.skills.versioning import SkillVersionManager

        checksum = sha256(content.encode("utf-8")).hexdigest()
        version_manager = SkillVersionManager(self.storage.base_dir)
        version_manager.record_version(
            skill_id=user_skill.skill_id,
            version=user_skill.metadata.version,
            author=metadata.get("author", "unknown"),
            message=metadata.get("message", "initial version"),
            file_path=user_skill.metadata.file_path,
            checksum=checksum,
        )

    def list_user_skills(self) -> list[Dict[str, Any]]:
        index = self._load_index()
        if index:
            return index
        if not self.storage.skills_dir.exists():
            return []
        skills = []
        for skill_dir in self.storage.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                content = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            metadata = self._parse_frontmatter(content)
            skills.append(
                {
                    "skill_id": skill_dir.name,
                    "name": metadata.get("name", skill_dir.name),
                    "description": metadata.get("description", ""),
                    "category": metadata.get("category", "custom"),
                    "created_at": metadata.get("created_at", ""),
                    "quality_score": None,
                    "risk_level": metadata.get("risk_level", "medium"),
                }
            )
        if skills:
            self._write_index(skills)
        return skills

    def scan_skill(self, skill_id: str) -> ScanResult:
        skill_dir = self._get_skill_dir(skill_id)
        scan_result = self.security_guard.scan_skill(skill_dir)
        index = self._load_index()
        for item in index:
            if item.get("skill_id") == skill_id:
                item["risk_level"] = scan_result.risk_level
        if index:
            self._write_index(index)
        return scan_result

    def evaluate_quality(self, skill_id: str):
        skill_dir = self._get_skill_dir(skill_id)
        skill_file = skill_dir / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")
        score = self.quality_evaluator.evaluate(content)
        index = self._load_index()
        for item in index:
            if item.get("skill_id") == skill_id:
                item["quality_score"] = score.overall
        if index:
            self._write_index(index)
        return score

    def _get_skill_dir(self, skill_id: str) -> Path:
        if not VALID_SKILL_ID_PATTERN.match(skill_id):
            raise ValidationError(f"技能ID格式无效: {skill_id}")
        skill_dir = self.storage.skills_dir / skill_id
        if not skill_dir.exists():
            raise ValidationError(f"技能不存在: {skill_id}")
        return skill_dir

    def _load_index(self) -> list[Dict[str, Any]]:
        index_file = self.storage.index_file
        if not index_file.exists():
            return []
        try:
            data = json.loads(index_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _write_index(self, entries: list[Dict[str, Any]]) -> None:
        self._atomic_write(self.storage.index_file, json.dumps(entries, ensure_ascii=False, indent=2))

    def _index_entry(self, user_skill: UserSkill) -> Dict[str, Any]:
        return {
            "skill_id": user_skill.skill_id,
            "name": user_skill.name,
            "description": user_skill.definition.description,
            "category": user_skill.category.value,
            "created_at": user_skill.metadata.created_at.isoformat(),
            "quality_score": user_skill.metadata.quality_score.overall
            if user_skill.metadata.quality_score
            else None,
            "risk_level": user_skill.risk_level.value,
        }

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        frontmatter = parts[1].strip()
        try:
            data = yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError:
            data = {}
        return data if isinstance(data, dict) else {}
