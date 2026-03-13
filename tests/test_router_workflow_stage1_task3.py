import unittest
from unittest.mock import MagicMock

from aiops.workflows.router_workflow import synthesize_results


class TestRouterWorkflowStage1Task3(unittest.TestCase):
    def test_kb_only_negative_response_calls_router_llm(self) -> None:
        router_llm = MagicMock()
        router_llm.invoke = MagicMock(return_value=MagicMock(content="I don't know."))
        state = {
            "query": "How do I authenticate API requests?",
            "results": [{"source": "knowledge_base", "result": "I don't know."}],
            "final_answer": "",
        }

        update = synthesize_results(state, router_llm)

        self.assertEqual(update["final_answer"], "I don't know.")
        router_llm.invoke.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
