import json
import tempfile
import unittest
from pathlib import Path

from aiops.skills.commands import SkillCommandsManager
from aiops.skills.manager import SkillManager


class TestSkillChaos(unittest.TestCase):
    def test_corrupted_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            manager = SkillManager(base_dir=base_dir)
            index_path = base_dir / "skills" / ".index.json"
            index_path.write_text("{bad json", encoding="utf-8")
            skills = manager.list_user_skills()
            self.assertEqual(skills, [])

    def test_missing_skill_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()
            missing_dir = skills_dir / "monitoring-missing"
            missing_dir.mkdir()
            commands = SkillCommandsManager(skills_dir=skills_dir, cache_path=Path(tmpdir) / "cache.json")
            self.assertEqual(commands.list_commands(), [])

    def test_partial_index_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            skills_dir = base_dir / "skills"
            skills_dir.mkdir(parents=True, exist_ok=True)
            (skills_dir / ".index.json").write_text(
                json.dumps([{"skill_id": "invalid"}]), encoding="utf-8"
            )
            manager = SkillManager(base_dir=base_dir)
            self.assertIsInstance(manager.list_user_skills(), list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
