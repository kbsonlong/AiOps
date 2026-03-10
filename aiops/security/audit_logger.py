from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


@dataclass(slots=True)
class AuditLogger:
    events: List[Dict[str, object]] = field(default_factory=list)

    def log(self, action: str, status: str, details: Dict[str, object] | None = None) -> None:
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "action": action,
            "status": status,
            "details": details or {},
        }
        self.events.append(entry)
