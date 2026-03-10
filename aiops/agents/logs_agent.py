from __future__ import annotations

from aiops.agents.base_agent import BaseAgent
from aiops.tools import (
    analyze_log_patterns,
    collect_system_logs,
    correlate_log_events,
    detect_log_anomalies,
    query_otel_logs,
    query_victorialogs,
    search_logs,
)


SYSTEM_PROMPT = (
    "You are a log analysis expert. You collect and analyze system and "
    "application logs, detect anomalies, and correlate events for diagnosis."
)


def build_logs_agent() -> BaseAgent:
    tools = [
        collect_system_logs,
        analyze_log_patterns,
        detect_log_anomalies,
        correlate_log_events,
        search_logs,
        query_victorialogs,
        query_otel_logs,
    ]
    return BaseAgent(name="logs", system_prompt=SYSTEM_PROMPT, tools=tools)
