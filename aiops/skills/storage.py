from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aiops.config.settings import load_settings


VALID_SKILL_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class SkillStoragePaths:
    base_dir: Path
    skills_dir: Path
    cache_dir: Path
    logs_dir: Path
    index_file: Path
    commands_cache: Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "skill"


def _expand_path(path_str: str) -> Path:
    expanded = os.path.expanduser(path_str)
    return Path(expanded).resolve()


def resolve_skills_base_dir(base_dir: Optional[Path] = None) -> Path:
    if base_dir is not None:
        return base_dir.expanduser().resolve()
    settings = load_settings()
    return _expand_path(settings.skills.base_dir)


def init_storage(base_dir: Optional[Path] = None) -> SkillStoragePaths:
    base = resolve_skills_base_dir(base_dir)
    skills_dir = base / "skills"
    cache_dir = base / "cache"
    logs_dir = base / "logs"
    index_file = skills_dir / ".index.json"
    commands_cache = cache_dir / "commands.json"

    skills_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return SkillStoragePaths(
        base_dir=base,
        skills_dir=skills_dir,
        cache_dir=cache_dir,
        logs_dir=logs_dir,
        index_file=index_file,
        commands_cache=commands_cache,
    )
