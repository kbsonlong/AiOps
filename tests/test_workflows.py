import unittest

from aiops.workflows.router_workflow import route_to_agents


class TestRouterWorkflow(unittest.TestCase):
    def test_route_to_agents_adds_fault_and_security(self) -> None:
        state = {
            "query": "CPU high and latency spike",
            "classifications": [
                {"source": "metrics", "query": "check CPU", "severity": "high"},
            ],
            "results": [],
            "final_answer": "",
        }
        sends = route_to_agents(state)
        targets = {send.node for send in sends}
        self.assertIn("metrics", targets)
        self.assertIn("fault", targets)
        self.assertIn("security", targets)

    def test_skill_orchestration_node(self) -> None:
        from aiops.workflows.router_workflow import skill_orchestration_node

        state = {
            "query": "query cpu metrics",
            "classifications": [],
            "results": [],
            "final_answer": "",
            "detected_skills": [],
            "skill_execution_plan": {},
        }
        update = skill_orchestration_node(state)
        self.assertIn("detected_skills", update)
        self.assertIn("skill_execution_plan", update)


if __name__ == "__main__":
    unittest.main(verbosity=2)
