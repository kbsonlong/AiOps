from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(slots=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str


class SkillSandbox:
    """Best-effort sandbox execution using subprocess with basic limits."""

    def __init__(self, timeout: int = 30, env: Optional[Dict[str, str]] = None) -> None:
        self.timeout = timeout
        self.env = env

    def run(self, command: List[str], cwd: Optional[str] = None) -> SandboxResult:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd,
                env=self.env,
            )
            return SandboxResult(
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(returncode=124, stdout=exc.stdout or "", stderr="timeout")
