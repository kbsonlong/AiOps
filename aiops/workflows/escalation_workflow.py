from __future__ import annotations

from typing import Literal, TypedDict


Severity = Literal["low", "medium", "high", "critical"]


class EscalationDecision(TypedDict):
    severity: Severity
    requires_human_approval: bool
    reason: str


def decide_escalation(severity: Severity) -> EscalationDecision:
    requires = severity in ("high", "critical")
    reason = "High risk or critical impact" if requires else "Within automated handling scope"
    return {
        "severity": severity,
        "requires_human_approval": requires,
        "reason": reason,
    }
