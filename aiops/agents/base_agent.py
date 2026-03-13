from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, List

from langchain.agents import create_agent
from langchain.tools import tool as lc_tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable, RunnableLambda


ToolFn = Callable[..., object]


@dataclass(slots=True)
class BaseAgent:
    name: str
    system_prompt: str
    tools: List[ToolFn]

    def build(self, llm) -> Runnable:
        """Build a LangChain agent with tools and prompt.

        For models that support tool calling natively (OpenAI, Anthropic), uses create_agent.
        For others (Ollama, etc.), falls back to a simpler ReAct-style implementation.
        """
        wrapped = [lc_tool(fn) for fn in self.tools]
        tool_map = {t.name: t for t in wrapped}
        tool_names = list(tool_map.keys())
        tool_descs = "\n".join([f"- {name}: {t.description}" for name, t in tool_map.items()])

        def simple_agent(inputs: dict) -> dict:
            """Simple ReAct-style agent that doesn't rely on native tool calling."""
            messages = inputs.get("messages", [])
            # Extract system prompt if present
            system_content = self.system_prompt

            # Build message list for LLM
            lc_messages = []
            if system_content:
                lc_messages.append(SystemMessage(content=system_content))
            lc_messages.extend(messages)

            # ReAct prompt
            react_prompt = f"""You are a helpful assistant with access to the following tools:

{tool_descs}

When you need to use a tool, respond with a JSON object in this format:
{{
  "tool": "tool_name",
  "arguments": {{"arg1": "value1", "arg2": "value2"}}
}}

If you have all the information to answer, respond normally with text.

Current conversation:"""

            max_iterations = 5
            for iteration in range(max_iterations):
                # Add ReAct instructions and conversation to messages
                full_messages = [SystemMessage(content=react_prompt)] + lc_messages

                try:
                    response = llm.invoke(full_messages)
                except Exception as e:
                    return {"messages": lc_messages + [AIMessage(content=f"Error: {e}")]}

                lc_messages.append(response)

                # Try to extract tool call
                content = response.content or ""
                tool_call = None

                # Try to parse the entire response as JSON first
                try:
                    parsed = json.loads(content.strip())
                    if isinstance(parsed, dict) and "tool" in parsed:
                        tool_call = parsed
                except json.JSONDecodeError:
                    pass

                # If that fails, try to extract JSON from text (handle nested objects)
                if not tool_call:
                    # Look for JSON-like patterns with "tool" key
                    json_match = re.search(r'\{[^{}]*"tool"\s*:\s*"[^"]*"[^{}]*\}', content)
                    if json_match:
                        try:
                            tool_data = json.loads(json_match.group(0))
                            if isinstance(tool_data, dict) and "tool" in tool_data:
                                tool_call = tool_data
                        except json.JSONDecodeError:
                            pass

                if tool_call and tool_call["tool"] in tool_map:
                    # Execute the tool
                    tool_name = tool_call["tool"]
                    tool_args = tool_call.get("arguments", {})

                    try:
                        # Get the tool (LangChain StructuredTool)
                        tool_obj = tool_map[tool_name]

                        # Call the tool - LangChain tools expect a dict input
                        if isinstance(tool_args, dict):
                            result = tool_obj.invoke(tool_args)
                        else:
                            # No arguments, pass empty dict
                            result = tool_obj.invoke({})
                    except Exception as e:
                        result = f"Tool execution error: {e}"

                    # Add tool result message
                    lc_messages.append(ToolMessage(content=str(result), tool_call_id=tool_name))
                else:
                    # No tool call found, assume this is the final answer
                    break

            # After iterations, return a summary based on tool results
            tool_results = [m for m in lc_messages if isinstance(m, ToolMessage)]
            if tool_results and len(lc_messages) > len(tool_results) + 1:
                # We have tool results but no final answer - generate one
                last_ai = lc_messages[-1]
                summary = f"Based on the tool execution results, here's what I found:\n\n"
                for tr in tool_results:
                    summary += f"- Tool {tr.tool_call_id}: {tr.content[:200]}...\n"
                # Replace the last AI message with a proper summary
                lc_messages[-1] = AIMessage(content=summary)

            return {"messages": lc_messages}

        # Detect if we should use native tool calling or fallback
        # Check if the LLM provider is one that supports native tool calling well
        # (OpenAI, Anthropic, etc.) vs others that need fallback (Ollama, etc.)
        model_str = str(getattr(llm, 'model', ''))
        provider_str = str(type(llm).__module__).lower()

        # Use native agent for known good providers
        use_native = any(x in provider_str or x in model_str for x in ['openai', 'anthropic', 'azure'])

        if use_native:
            try:
                llm_with_tools = llm.bind_tools(wrapped)
                return create_agent(llm_with_tools, tools=wrapped, system_prompt=self.system_prompt)
            except Exception:
                pass  # Fall through to simple agent

        # For Ollama and other providers, use simple ReAct-style agent
        return RunnableLambda(simple_agent)

    @staticmethod
    def ensure_tools(tools: Iterable[ToolFn]) -> List[ToolFn]:
        return list(tools)
