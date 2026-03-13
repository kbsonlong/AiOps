import unittest
from unittest.mock import MagicMock, patch

from aiops.workflows.middleware_chain import MiddlewareChain
from aiops.workflows.router_workflow import (
    make_skill_middleware_pre_node,
    make_synthesize_with_middlewares_node,
)


class TestMiddlewareChainStage2Task4(unittest.IsolatedAsyncioTestCase):
    async def test_chain_order_and_async_support(self) -> None:
        async def mw1(state, call_next):
            state = {**state, "trace": list(state.get("trace", [])) + ["mw1_pre"]}
            out = await call_next(state)
            return {**out, "trace": list(out.get("trace", [])) + ["mw1_post"]}

        async def mw2(state, call_next):
            state = {**state, "trace": list(state.get("trace", [])) + ["mw2_pre"]}
            out = await call_next(state)
            return {**out, "trace": list(out.get("trace", [])) + ["mw2_post"]}

        def terminal(state):
            return {**state, "trace": list(state.get("trace", [])) + ["terminal"]}

        chain = MiddlewareChain().add(mw1).add(mw2)
        out = await chain.arun({"trace": []}, terminal=terminal)
        self.assertEqual(out["trace"], ["mw1_pre", "mw2_pre", "terminal", "mw2_post", "mw1_post"])

    async def test_chain_short_circuit(self) -> None:
        async def short(state, call_next):
            return {"trace": ["short"]}

        def terminal(state):
            return {"trace": ["terminal"]}

        out = await MiddlewareChain().add(short).arun({"trace": []}, terminal=terminal)
        self.assertEqual(out["trace"], ["short"])


class DummyCommands:
    def list_commands(self):
        return ["/demo"]

    def get_command_content(self, command: str):
        if command == "/demo":
            return "DEMO CONTENT"
        return None


class TestWorkflowMiddlewareIntegrationStage2Task4(unittest.TestCase):
    def test_skill_middleware_pre_node_uses_chain(self) -> None:
        node = make_skill_middleware_pre_node()
        with patch("aiops.workflows.skill_middleware.get_skill_commands_manager", return_value=DummyCommands()):
            update = node({"query": "/demo run it", "context": {}})
        self.assertIn("DEMO CONTENT", update["query"])
        self.assertTrue(update["context"]["skill_invoked"])
        self.assertNotIn("results", update)

    def test_synthesize_node_applies_post_middleware(self) -> None:
        router_llm = MagicMock()
        router_llm.invoke = MagicMock(return_value=MagicMock(content="1. a\n2. b\n3. c\n4. d\n5. e\n"))
        node = make_synthesize_with_middlewares_node(router_llm)
        state = {
            "query": "fix error",
            "results": [{"source": "logs", "result": "ok"}],
            "context": {},
            "final_answer": "",
        }
        with patch("aiops.workflows.skill_middleware._auto_create_skill", return_value=False):
            update = node(state)
        self.assertIn("系统提示", update["final_answer"])
        self.assertNotIn("results", update)


if __name__ == "__main__":
    unittest.main(verbosity=2)
