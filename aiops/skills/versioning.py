from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from aiops.skills.exceptions import ValidationError
from aiops.skills.storage import VALID_SKILL_ID_PATTERN, init_storage


@dataclass(slots=True)
class SkillVersionEntry:
    version: str
    created_at: str
    author: str
    message: str
    file_path: str
    checksum: str


class SkillVersionManager:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.storage = init_storage(base_dir)

    def list_versions(self, skill_id: str) -> List[SkillVersionEntry]:
        data = self._load_version_index(skill_id)
        return [SkillVersionEntry(**item) for item in data]

    def record_version(
        self,
        skill_id: str,
        version: str,
        author: str,
        message: str,
        file_path: Path,
        checksum: str,
    ) -> SkillVersionEntry:
        entry = SkillVersionEntry(
            version=version,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            author=author,
            message=message,
            file_path=str(file_path),
            checksum=checksum,
        )
        data = self._load_version_index(skill_id)
        data.append(
            {
                "version": entry.version,
                "created_at": entry.created_at,
                "author": entry.author,
                "message": entry.message,
                "file_path": entry.file_path,
                "checksum": entry.checksum,
            }
        )
        self._write_version_index(skill_id, data)
        return entry

    def _load_version_index(self, skill_id: str) -> List[Dict]:
        version_file = self._version_index_file(skill_id)
        if not version_file.exists():
            return []
        try:
            data = json.loads(version_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _write_version_index(self, skill_id: str, data: List[Dict]) -> None:
        version_file = self._version_index_file(skill_id)
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _version_index_file(self, skill_id: str) -> Path:
        if not VALID_SKILL_ID_PATTERN.match(skill_id):
            raise ValidationError(f"技能ID格式无效: {skill_id}")
        return self.storage.skills_dir / skill_id / "versions.json"
