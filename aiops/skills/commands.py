from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from aiops.skills.storage import init_storage, slugify


class SkillCommandsManager:
    """Scan skills directory and expose commands with lazy content loading."""

    def __init__(self, skills_dir: Optional[Path] = None, cache_path: Optional[Path] = None):
        if skills_dir is None and cache_path is None:
            storage = init_storage()
            self.skills_dir = storage.skills_dir
            self.cache_path = storage.commands_cache
        else:
            self.skills_dir = skills_dir or init_storage().skills_dir
            if cache_path is None:
                cache_dir = self.skills_dir.parent / "cache"
                self.cache_path = cache_dir / "commands.json"
            else:
                self.cache_path = cache_path
        self.commands_cache: Dict[str, Dict] = {}
        self._scan_commands()

    def list_commands(self) -> List[str]:
        return sorted(self.commands_cache.keys())

    def get_command_content(self, command: str) -> Optional[str]:
        cmd_info = self.commands_cache.get(command)
        if not cmd_info:
            return None
        if not cmd_info["loaded"]:
            try:
                content = cmd_info["skill_file"].read_text(encoding="utf-8")
                cmd_info["content"] = content
                cmd_info["loaded"] = True
            except OSError:
                return None
        return self._format_skill_response(cmd_info)

    def _scan_commands(self) -> None:
        self.commands_cache.clear()
        if not self.skills_dir.exists():
            return
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                content = skill_file.read_text(encoding="utf-8")
                metadata = self._parse_frontmatter(content)
            except OSError:
                continue
            skill_id = skill_dir.name
            skill_name = metadata.get("name", skill_id)
            description = metadata.get("description", "")
            category = metadata.get("category", "custom")
            cmd_slug = self._generate_command_slug(skill_id, skill_name)
            self.commands_cache[f"/{cmd_slug}"] = {
                "skill_id": skill_id,
                "skill_name": skill_name,
                "description": description,
                "category": category,
                "skill_file": skill_file,
                "skill_dir": skill_dir,
                "loaded": False,
                "content": None,
            }
        self._persist_cache()

    def _persist_cache(self) -> None:
        payload = {
            "commands": [
                {
                    "command": cmd,
                    "skill_id": info["skill_id"],
                    "skill_name": info["skill_name"],
                    "description": info["description"],
                    "category": info["category"],
                }
                for cmd, info in self.commands_cache.items()
            ]
        }
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            return

    def _parse_frontmatter(self, content: str) -> Dict:
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

    def _generate_command_slug(self, skill_id: str, skill_name: str) -> str:
        if skill_id:
            return slugify(skill_id)
        return slugify(skill_name)

    def _format_skill_response(self, cmd_info: Dict) -> str:
        skill_name = cmd_info["skill_name"]
        content = cmd_info["content"] or ""
        sections = self._extract_key_sections(content)
        parts = [
            f'[SYSTEM: 用户调用了 "{skill_name}" 技能。相关指令如下：]',
            "",
            *sections,
            "",
            '[SYSTEM: 请根据以上指令执行操作。如需完整技能内容，请说"显示完整技能"。]',
        ]
        return "\n".join(parts)

    def _extract_key_sections(self, content: str) -> List[str]:
        key_sections: List[str] = []
        section_patterns = [
            (r"^##?\s+概述[^\n]*\n(.*?)(?=\n##?\s+)", "概述"),
            (r"^##?\s+输入参数[^\n]*\n(.*?)(?=\n##?\s+)", "输入参数"),
            (r"^##?\s+执行步骤[^\n]*\n(.*?)(?=\n##?\s+)", "执行步骤（前3步）"),
            (r"^##?\s+输出格式[^\n]*\n(.*?)(?=\n##?\s+)", "输出格式"),
        ]
        for pattern, section_name in section_patterns:
            match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
            if not match:
                continue
            section_content = match.group(1).strip()
            if len(section_content) > 500:
                section_content = section_content[:500] + "..."
            key_sections.append(f"### {section_name}\n{section_content}")
        return key_sections
