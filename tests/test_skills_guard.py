import tempfile
import unittest
from pathlib import Path

from aiops.skills.guard import SkillsGuard


class TestSkillsGuard(unittest.TestCase):
    def test_detects_dangerous_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("rm -rf /\n", encoding="utf-8")
            guard = SkillsGuard()
            result = guard.scan_skill(skill_dir)
            self.assertEqual(result.risk_level, "dangerous")
            self.assertTrue(result.issues)

    def test_whitelist_allows_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("systemctl status prometheus\n", encoding="utf-8")
            guard = SkillsGuard()
            result = guard.scan_skill(skill_dir)
            self.assertEqual(result.risk_level, "safe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
