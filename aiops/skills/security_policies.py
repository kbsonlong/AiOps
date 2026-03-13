from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(slots=True)
class SandboxPolicy:
    allowed_commands: List[str]
    blocked_commands: List[str]

    def is_allowed(self, command: str) -> bool:
        if any(command.startswith(item) for item in self.blocked_commands):
            return False
        if not self.allowed_commands:
            return True
        return any(command.startswith(item) for item in self.allowed_commands)
