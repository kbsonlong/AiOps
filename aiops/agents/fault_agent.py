from __future__ import annotations

from aiops.agents.base_agent import BaseAgent
from aiops.tools import (
    analyze_root_cause,
    assess_impact,
    diagnose_fault,
    recommend_solutions,
    validate_solution,
)


SYSTEM_PROMPT = (
    "You are a fault diagnosis expert. You analyze symptoms, identify root "
    "causes, assess impact, and recommend validated remediation steps."
)


def build_fault_agent() -> BaseAgent:
    tools = [
        diagnose_fault,
        analyze_root_cause,
        assess_impact,
        recommend_solutions,
        validate_solution,
    ]
    return BaseAgent(name="fault", system_prompt=SYSTEM_PROMPT, tools=tools)
