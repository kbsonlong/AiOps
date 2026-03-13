import unittest

from aiops.skills.sandbox import SkillSandbox


class TestSkillSandbox(unittest.TestCase):
    def test_run_command(self) -> None:
        sandbox = SkillSandbox(timeout=5)
        result = sandbox.run(["echo", "hello"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("hello", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
