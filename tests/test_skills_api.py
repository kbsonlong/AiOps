import unittest

from aiops.api.skill_api import build_registry, discover_skills, list_skills


class TestSkillsApi(unittest.TestCase):
    def test_list_skills(self) -> None:
        result = list_skills()
        self.assertTrue(isinstance(result, list))
        self.assertGreaterEqual(len(result), 1)

    def test_discover_skills(self) -> None:
        result = discover_skills(query="cpu", category=None, tag=["prometheus"])
        self.assertTrue(isinstance(result, list))


if __name__ == "__main__":
    unittest.main(verbosity=2)
