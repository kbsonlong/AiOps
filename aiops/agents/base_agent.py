from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List

from langchain.agents import create_agent
from langchain.tools import tool as lc_tool


ToolFn = Callable[..., object]


@dataclass(slots=True)
class BaseAgent:
    name: str
    system_prompt: str
    tools: List[ToolFn]

    def build(self, llm) -> object:
        """Build a LangChain agent with tools and prompt."""
        wrapped = [lc_tool(fn) for fn in self.tools]
        return create_agent(llm, tools=wrapped, system_prompt=self.system_prompt)

    @staticmethod
    def ensure_tools(tools: Iterable[ToolFn]) -> List[ToolFn]:
        return list(tools)
