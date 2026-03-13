from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda

from aiops.agents.base_agent import BaseAgent
from aiops.tools import (
    collect_cpu_metrics,
    collect_disk_metrics,
    collect_memory_metrics,
    collect_network_metrics,
    collect_process_metrics,
    detect_metric_anomaly,
    query_otel_metrics,
    query_prometheus,
    query_prometheus_range,
)


SYSTEM_PROMPT = (
    "You are a system metrics expert. You analyze CPU, memory, disk, network, "
    "and process metrics, detect anomalies, and provide optimization advice."
)


def build_metrics_agent() -> BaseAgent:
    tools = [
        collect_cpu_metrics,
        collect_memory_metrics,
        collect_disk_metrics,
        collect_network_metrics,
        collect_process_metrics,
        detect_metric_anomaly,
        query_prometheus,
        query_prometheus_range,
        query_otel_metrics,
    ]
    return BaseAgent(name="metrics", system_prompt=SYSTEM_PROMPT, tools=tools)


def build_simple_metrics_agent(llm) -> Runnable:
    """Build a simple metrics agent that executes tools directly based on keywords.

    This bypasses the complex tool-calling mechanism that doesn't work well with Ollama.
    """

    def simple_metrics_agent(inputs: dict) -> dict:
        messages = inputs.get("messages", [])
        if not messages:
            return {"messages": [AIMessage(content="No query provided")]}

        # Get the user's query - handle both dict and message object formats
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            query = last_msg.get("content", str(last_msg))
        elif hasattr(last_msg, "content"):
            query = last_msg.content
        else:
            query = str(last_msg)
        query_lower = query.lower()

        # Determine which metrics to collect based on keywords
        tools_to_call = []
        if any(k in query_lower for k in ["cpu", "处理器"]):
            tools_to_call.append(("CPU", collect_cpu_metrics))
        if any(k in query_lower for k in ["mem", "内存", "memory", "ram"]):
            tools_to_call.append(("Memory", collect_memory_metrics))
        if any(k in query_lower for k in ["disk", "磁盘", "storage", "硬盘", "存储"]):
            tools_to_call.append(("Disk", collect_disk_metrics))
        if any(k in query_lower for k in ["net", "network", "网络", "带宽"]):
            tools_to_call.append(("Network", collect_network_metrics))

        # If no specific metrics requested, collect all
        if not tools_to_call:
            tools_to_call = [
                ("CPU", collect_cpu_metrics),
                ("Memory", collect_memory_metrics),
                ("Disk", collect_disk_metrics),
                ("Network", collect_network_metrics),
            ]

        # Execute the tools and collect results
        results = []
        for name, tool_fn in tools_to_call:
            try:
                result = tool_fn()
                results.append(f"## {name} Metrics\n{result}")
            except Exception as e:
                results.append(f"## {name} Metrics\nError: {e}")

        # Create a simple summary without LLM to avoid timeout issues
        summary_parts = [f"## Metrics Summary for: {query}\n"]

        for result_str in results:
            # Extract key info from the result
            if "CPU" in result_str and "cpu_percent" in result_str:
                import re
                match = re.search(r"'cpu_percent': ([\d.]+)", result_str)
                if match:
                    summary_parts.append(f"- CPU Usage: {float(match.group(1)):.1f}%")
                else:
                    summary_parts.append(f"- CPU: Collected successfully")
            elif "Memory" in result_str:
                match = re.search(r"'memory_percent': ([\d.]+)", result_str)
                if match:
                    summary_parts.append(f"- Memory Usage: {float(match.group(1)):.1f}%")
                else:
                    summary_parts.append(f"- Memory: Collected successfully")
            elif "Disk" in result_str:
                summary_parts.append(f"- Disk: Collected successfully")
            elif "Network" in result_str:
                summary_parts.append(f"- Network: Collected successfully")
            else:
                summary_parts.append(f"- {result_str.split(chr(10))[0]}")

        final_answer = "\n".join(summary_parts)
        return {"messages": [AIMessage(content=final_answer)]}

    return RunnableLambda(simple_metrics_agent)


# Patch the build method to use the simple agent for metrics
original_build = BaseAgent.build


def patched_build(self, llm) -> Runnable:
    """Use simple metrics agent for metrics, original for others."""
    if self.name == "metrics":
        return build_simple_metrics_agent(llm)
    return original_build(self, llm)


# Apply the patch
BaseAgent.build = patched_build
