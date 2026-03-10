from __future__ import annotations

from aiops.agents.base_agent import BaseAgent
from aiops.tools import (
    assess_compliance,
    audit_access_logs,
    check_security_config,
    detect_security_threats,
    scan_vulnerabilities,
)


SYSTEM_PROMPT = (
    "You are a security audit expert. You review security configuration, "
    "audit access logs, detect threats, and assess compliance."
)


def build_security_agent() -> BaseAgent:
    tools = [
        scan_vulnerabilities,
        check_security_config,
        audit_access_logs,
        detect_security_threats,
        assess_compliance,
    ]
    return BaseAgent(name="security", system_prompt=SYSTEM_PROMPT, tools=tools)
