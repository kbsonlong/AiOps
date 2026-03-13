import tempfile
import unittest
from pathlib import Path

from aiops.auth.skill_permissions import SkillPermissionChecker
from aiops.skills.guard import SkillsGuard


class TestPenetration(unittest.TestCase):
    def test_guard_blocks_rm_root(self) -> None:
        guard = SkillsGuard()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("rm -rf /\n", encoding="utf-8")
            result = guard.scan_skill(skill_dir)
            self.assertEqual(result.risk_level, "dangerous")

    def test_guard_allows_whitelisted(self) -> None:
        guard = SkillsGuard()
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("systemctl status prometheus\n", encoding="utf-8")
            result = guard.scan_skill(skill_dir)
            self.assertEqual(result.risk_level, "safe")

    def test_permission_checker_denies(self) -> None:
        checker = SkillPermissionChecker(allow_create=False)
        with self.assertRaises(PermissionError):
            checker.ensure_allowed("create")


if __name__ == "__main__":
    unittest.main(verbosity=2)
