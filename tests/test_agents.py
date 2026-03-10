import unittest

from aiops.agents import (
    build_fault_agent,
    build_logs_agent,
    build_metrics_agent,
    build_security_agent,
)


class TestAgents(unittest.TestCase):
    def test_metrics_agent(self) -> None:
        agent = build_metrics_agent()
        self.assertEqual(agent.name, "metrics")
        self.assertGreaterEqual(len(agent.tools), 6)

    def test_logs_agent(self) -> None:
        agent = build_logs_agent()
        self.assertEqual(agent.name, "logs")
        self.assertIn("log", agent.system_prompt.lower())

    def test_fault_agent(self) -> None:
        agent = build_fault_agent()
        self.assertEqual(agent.name, "fault")
        self.assertIn("fault", agent.system_prompt.lower())

    def test_security_agent(self) -> None:
        agent = build_security_agent()
        self.assertEqual(agent.name, "security")
        self.assertIn("security", agent.system_prompt.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)

