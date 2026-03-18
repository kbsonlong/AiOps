import asyncio
import unittest
from unittest.mock import patch

from aiops.workflows.middleware_chain import MiddlewareChain
from aiops.workflows.router_workflow import (
    make_skill_middleware_pre_node,
    make_synthesize_with_middlewares_node,
)


class TestWorkflowMiddlewareNodes(unittest.TestCase):
    def test_skill_middleware_pre_node_runs_in_event_loop(self) -> None:
        async def mw(state, call_next):
            updated = {**state, "query": "enhanced", "context": {"k": "v"}}
            return await call_next(updated)

        chain = MiddlewareChain().add(mw)

        with patch(
            "aiops.workflows.router_workflow.get_skill_pre_middleware_chain",
            return_value=chain,
        ):
            node = make_skill_middleware_pre_node()

            async def run():
                state = {"query": "raw", "context": {}}
                return await node(state)

            update = asyncio.run(run())

        self.assertEqual(update["query"], "enhanced")
        self.assertEqual(update["context"], {"k": "v"})

    def test_synthesize_node_runs_in_event_loop(self) -> None:
        async def mw(state, call_next):
            updated = {**state, "context": {**state.get("context", {}), "post": True}}
            return await call_next(updated)

        chain = MiddlewareChain().add(mw)

        with (
            patch(
                "aiops.workflows.router_workflow.get_skill_post_middleware_chain",
                return_value=chain,
            ),
            patch(
                "aiops.workflows.router_workflow.synthesize_results",
                return_value={"final_answer": "OK"},
            ),
        ):
            node = make_synthesize_with_middlewares_node(router_llm=None)

            async def run():
                state = {"query": "q", "results": [], "context": {}}
                return await node(state)

            update = asyncio.run(run())

        self.assertEqual(update["final_answer"], "OK")
        self.assertEqual(update["context"], {"post": True})


if __name__ == "__main__":
    unittest.main(verbosity=2)

