import unittest

from aiops.workflows.escalation_workflow import decide_escalation


class TestEscalation(unittest.TestCase):
    def test_decide_escalation(self) -> None:
        decision = decide_escalation("critical")
        self.assertTrue(decision["requires_human_approval"])
        decision_low = decide_escalation("low")
        self.assertFalse(decision_low["requires_human_approval"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

