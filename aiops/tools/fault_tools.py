from __future__ import annotations

from typing import Dict, List


def diagnose_fault(symptoms: str) -> Dict[str, str]:
    """Diagnose fault based on a symptom description."""
    text = symptoms.lower()
    if "cpu" in text and ("high" in text or "100%" in text):
        fault = "high_cpu"
        cause = "CPU saturation or runaway process"
    elif "memory" in text or "oom" in text:
        fault = "memory_pressure"
        cause = "Memory leak or insufficient memory"
    elif "disk" in text and ("full" in text or "space" in text):
        fault = "disk_full"
        cause = "Disk usage exceeded capacity"
    elif "network" in text and ("timeout" in text or "latency" in text):
        fault = "network_latency"
        cause = "Network congestion or remote dependency issues"
    else:
        fault = "unknown"
        cause = "Insufficient data for diagnosis"

    return {"fault_type": fault, "likely_cause": cause}


def analyze_root_cause(metrics: Dict[str, float], logs: List[str]) -> Dict[str, str]:
    """Analyze root cause based on metrics and logs."""
    cause = "undetermined"
    if metrics.get("cpu_percent", 0) >= 90:
        cause = "High CPU utilization detected"
    elif metrics.get("memory_percent", 0) >= 90:
        cause = "High memory utilization detected"
    elif metrics.get("disk_percent", 0) >= 90:
        cause = "Disk nearly full"

    if any("exception" in log.lower() for log in logs):
        cause = "Application exceptions detected in logs"

    return {"root_cause": cause}


def assess_impact(fault_type: str) -> Dict[str, str]:
    """Assess impact severity for a fault type."""
    mapping = {
        "high_cpu": "medium",
        "memory_pressure": "high",
        "disk_full": "high",
        "network_latency": "medium",
        "unknown": "low",
    }
    return {"fault_type": fault_type, "severity": mapping.get(fault_type, "low")}


def recommend_solutions(fault_analysis: str) -> Dict[str, List[str]]:
    """Recommend solutions for a fault analysis summary."""
    text = fault_analysis.lower()
    recommendations: list[str] = []
    if "cpu" in text:
        recommendations.append("Identify and restart the runaway process")
        recommendations.append("Scale out or increase CPU allocation")
    if "memory" in text:
        recommendations.append("Restart services to clear memory leak")
        recommendations.append("Increase memory limits")
    if "disk" in text:
        recommendations.append("Clear temp files or rotate logs")
        recommendations.append("Expand disk capacity")
    if not recommendations:
        recommendations.append("Collect more metrics and logs for analysis")
    return {"recommendations": recommendations}


def validate_solution(solution: str, fault_context: str) -> Dict[str, str]:
    """Validate whether a solution matches the fault context."""
    ok = solution.lower() in fault_context.lower()
    return {
        "solution": solution,
        "is_valid": "yes" if ok else "unknown",
    }

