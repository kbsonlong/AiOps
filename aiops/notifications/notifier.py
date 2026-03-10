from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(slots=True)
class Notifier:
    channel: str = "console"

    def send(self, title: str, severity: str, details: Dict[str, object]) -> Dict[str, object]:
        return {
            "channel": self.channel,
            "title": title,
            "severity": severity,
            "details": details,
        }
