import tempfile
import unittest
from pathlib import Path

from aiops.skills.commands import SkillCommandsManager


SKILL_MD = """---
name: Demo Skill
description: Demo description
category: monitoring
---

## 概述
测试技能概述

## 输入参数
- a: 默认 1

## 执行步骤
1. 第一步
2. 第二步

## 输出格式
JSON
"""


class TestSkillCommands(unittest.TestCase):
    def test_scan_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()
            skill_dir = skills_dir / "monitoring-demo-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

            manager = SkillCommandsManager(skills_dir=skills_dir, cache_path=Path(tmpdir) / "commands.json")
            commands = manager.list_commands()
            self.assertTrue(commands)
            content = manager.get_command_content(commands[0])
            self.assertIn("Demo Skill", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
