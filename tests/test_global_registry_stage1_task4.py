import unittest
from unittest.mock import patch

import aiops.skills.global_registry as global_registry


class TestGlobalRegistryStage1Task4(unittest.TestCase):
    def setUp(self) -> None:
        global_registry._reset_global_skill_registry_for_tests()

    def tearDown(self) -> None:
        global_registry._reset_global_skill_registry_for_tests()

    def test_get_global_registry_returns_same_instance(self) -> None:
        first = global_registry.get_global_skill_registry()
        second = global_registry.get_global_skill_registry()
        self.assertIs(first, second)

    def test_builtin_registration_runs_only_once(self) -> None:
        with patch(
            "aiops.skills.global_registry.SkillRegistry.bulk_register",
            autospec=True,
            wraps=global_registry.SkillRegistry.bulk_register,
        ) as bulk_register:
            first = global_registry.get_global_skill_registry()
            second = global_registry.get_global_skill_registry()
            self.assertIs(first, second)
            self.assertEqual(bulk_register.call_count, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
