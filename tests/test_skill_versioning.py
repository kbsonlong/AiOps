import tempfile
import unittest
from pathlib import Path

from aiops.skills.versioning import SkillVersionManager


class TestSkillVersioning(unittest.TestCase):
    def test_record_and_list_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SkillVersionManager(base_dir=Path(tmpdir))
            entry = manager.record_version(
                skill_id="monitoring-demo-skill",
                version="1.0.0",
                author="tester",
                message="initial",
                file_path=Path(tmpdir) / "SKILL.md",
                checksum="abc",
            )
            versions = manager.list_versions("monitoring-demo-skill")
            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0].version, entry.version)


if __name__ == "__main__":
    unittest.main(verbosity=2)
