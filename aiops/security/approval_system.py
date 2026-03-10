from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(slots=True)
class ApprovalRequest:
    approval_id: str
    action: str
    context: Dict[str, object]
    approved_by: Optional[str] = None


@dataclass(slots=True)
class ApprovalSystem:
    requests: Dict[str, ApprovalRequest] = field(default_factory=dict)

    def request_approval(self, action: str, context: Dict[str, object]) -> str:
        approval_id = f"approval-{len(self.requests) + 1}"
        self.requests[approval_id] = ApprovalRequest(
            approval_id=approval_id,
            action=action,
            context=context,
        )
        return approval_id

    def approve(self, approval_id: str, approver: str) -> bool:
        req = self.requests.get(approval_id)
        if not req:
            return False
        req.approved_by = approver
        return True

    def is_approved(self, approval_id: str) -> bool:
        req = self.requests.get(approval_id)
        return bool(req and req.approved_by)
