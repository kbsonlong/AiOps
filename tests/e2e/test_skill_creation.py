import tempfile
import unittest
from pathlib import Path

from aiops.skills.commands import SkillCommandsManager
from aiops.skills.manager import SkillManager


CONTENT = """# 示例技能

## 概述
端到端测试技能。

## 输入参数
- target: 默认 localhost

## 执行步骤
1. 如果参数为空则使用默认值
2. 执行检查
3. 输出结果

## 输出格式
文本输出

## 注意事项
需要权限，谨慎执行，确认再执行，备份再操作，测试环境先验证。

示例：执行命令并输出结果。
"""


class TestSkillCreationE2E(unittest.TestCase):
    def test_create_and_register(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            manager = SkillManager(base_dir=base_dir)
            user_skill = manager.create_skill(
                name="E2E Skill",
                content=CONTENT,
                category="diagnosis",
                metadata={"description": "e2e", "author": "tester"},
            )
            skills_dir = base_dir / "skills"
            commands = SkillCommandsManager(skills_dir=skills_dir, cache_path=base_dir / "cache" / "commands.json")
            self.assertIn(f"/{user_skill.skill_id}", commands.list_commands())


if __name__ == "__main__":
    unittest.main(verbosity=2)
