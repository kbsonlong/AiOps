from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from aiops.config.security_config import SecurityConfig
from aiops.security.approval_system import ApprovalSystem
from aiops.security.audit_logger import AuditLogger


@dataclass(slots=True)
class SecurityController:
    config: SecurityConfig
    approval_system: ApprovalSystem = field(default_factory=ApprovalSystem)
    audit_logger: AuditLogger = field(default_factory=AuditLogger)

    def check_action(self, action: str, context: Optional[Dict[str, object]] = None) -> Dict[str, object]:
        allowed = action in self.config.allowed_actions
        requires_approval = bool(self.config.approval_required)
        approval_id = None
        if allowed and requires_approval:
            approval_id = self.approval_system.request_approval(action, context or {})
        status = "allowed" if allowed else "denied"
        self.audit_logger.log(action, status, {"approval_id": approval_id})
        return {
            "action": action,
            "allowed": allowed,
            "requires_approval": requires_approval and allowed,
            "approval_id": approval_id,
        }

    def enforce_action(self, action: str, approval_id: Optional[str] = None) -> bool:
        if action not in self.config.allowed_actions:
            self.audit_logger.log(action, "blocked", {"reason": "not_allowed"})
            return False
        if self.config.approval_required:
            if not approval_id or not self.approval_system.is_approved(approval_id):
                self.audit_logger.log(action, "blocked", {"reason": "not_approved"})
                return False
        self.audit_logger.log(action, "executed", {})
        return True
