import unittest

from aiops.config.security_config import SecurityConfig
from aiops.security.controller import SecurityController


class TestSecurityController(unittest.TestCase):
    def test_requires_approval(self) -> None:
        config = SecurityConfig(approval_required=True, allowed_actions=["read_logs"])
        controller = SecurityController(config=config)
        decision = controller.check_action("read_logs", {"scope": "system"})
        self.assertTrue(decision["allowed"])
        self.assertTrue(decision["requires_approval"])
        approval_id = decision["approval_id"]
        self.assertFalse(controller.enforce_action("read_logs", approval_id))
        controller.approval_system.approve(approval_id, "admin")
        self.assertTrue(controller.enforce_action("read_logs", approval_id))

    def test_denied_action(self) -> None:
        config = SecurityConfig(approval_required=False, allowed_actions=["read_logs"])
        controller = SecurityController(config=config)
        decision = controller.check_action("write_logs")
        self.assertFalse(decision["allowed"])
        self.assertFalse(controller.enforce_action("write_logs"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

