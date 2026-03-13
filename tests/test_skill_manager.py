import tempfile
import unittest
from pathlib import Path

from aiops.skills.exceptions import SecurityBlockedError, SkillQualityError
from aiops.skills.manager import SkillManager


GOOD_CONTENT = """# 技能标题

## 概述
这是一个测试技能。

## 输入参数
- threshold: 默认 80

## 执行步骤
1. 如果满足条件则继续
2. 执行命令
3. 检查结果

## 输出格式
返回 JSON 格式。

## 注意事项
需要权限，谨慎执行，确认再执行，备份再操作，测试环境先验证。

```bash
echo "ok"
```

示例：运行命令并返回结果。
"""


class TestSkillManager(unittest.TestCase):
    def test_create_skill_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(base_dir=Path(tmpdir))
            user_skill = manager.create_skill(
                name="Diagnose High CPU",
                content=GOOD_CONTENT,
                category="monitoring",
                metadata={
                    "description": "diagnose cpu",
                    "author": "tester",
                    "risk_level": "low",
                    "tags": ["cpu"],
                },
            )
            self.assertTrue((Path(tmpdir) / "skills" / user_skill.skill_id / "SKILL.md").exists())

    def test_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(base_dir=Path(tmpdir))
            with self.assertRaises(SkillQualityError):
                manager.create_skill(
                    name="Low Quality",
                    content="缺少关键章节",
                    category="monitoring",
                    metadata={"description": "bad"},
                )

    def test_security_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillManager(base_dir=Path(tmpdir))
            dangerous = GOOD_CONTENT + "\nrm -rf /\n"
            with self.assertRaises(SecurityBlockedError):
                manager.create_skill(
                    name="Dangerous Skill",
                    content=dangerous,
                    category="security",
                    metadata={"description": "bad"},
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
