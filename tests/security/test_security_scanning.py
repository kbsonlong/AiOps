import tempfile
import unittest
from pathlib import Path

from aiops.skills.guard import SkillsGuard


class TestSecurityScanning(unittest.TestCase):
    def test_aiops_specific_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "skill"
            skill_dir.mkdir()
            content = "systemctl stop prometheus\n"
            (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
            guard = SkillsGuard()
            result = guard.scan_skill(skill_dir)
            self.assertEqual(result.risk_level, "caution")
            self.assertTrue(result.issues)


if __name__ == "__main__":
    unittest.main(verbosity=2)
