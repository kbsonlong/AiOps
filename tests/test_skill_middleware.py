import unittest
from unittest.mock import patch

from aiops.workflows.skill_middleware import skill_integration_middleware, skill_solidification_middleware


class DummyCommands:
    def list_commands(self):
        return ["/demo"]

    def get_command_content(self, command: str):
        if command == "/demo":
            return "DEMO CONTENT"
        return None


class TestSkillMiddleware(unittest.TestCase):
    def test_skill_integration_middleware(self) -> None:
        state = {"query": "/demo run it"}
        with patch("aiops.workflows.skill_middleware.get_skill_commands_manager", return_value=DummyCommands()):
            updated = skill_integration_middleware(state)
        self.assertIn("DEMO CONTENT", updated["query"])
        self.assertTrue(updated["context"]["skill_invoked"])

    def test_skill_solidification_middleware(self) -> None:
        state = {"query": "fix error"}
        next_state = {
            "final_answer": "1. step\n2. step\n3. step\n4. step\n5. step\n",
            "context": {},
        }
        updated = skill_solidification_middleware(state, next_state)
        self.assertIn("系统提示", updated["final_answer"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
