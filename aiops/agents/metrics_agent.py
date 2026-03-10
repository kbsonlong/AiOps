from __future__ import annotations

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
