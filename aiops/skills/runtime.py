from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from aiops.security.controller import SecurityController
from aiops.skills.models import SkillDefinition


@dataclass(slots=True)
class SkillExecutionResult:
    skill_id: str
    success: bool
    outputs: Dict[str, Any]
    execution_time: float
    timestamp: float
    error: Optional[str] = None


class SkillExecutionRuntime:
    def __init__(self, security_controller: SecurityController) -> None:
        self.security_controller = security_controller

    def execute_skill(
        self,
        skill_def: SkillDefinition,
        inputs: Dict[str, Any],
        executor,
    ) -> SkillExecutionResult:
        decision = self.security_controller.check_action(
            action=skill_def.id,
            context={"inputs": inputs, "risk_level": skill_def.risk_level},
        )
        if not decision["allowed"]:
            return SkillExecutionResult(
                skill_id=skill_def.id,
                success=False,
                outputs={},
                execution_time=0.0,
                timestamp=time.time(),
                error="action_not_allowed",
            )
        if decision["requires_approval"]:
            return SkillExecutionResult(
                skill_id=skill_def.id,
                success=False,
                outputs={},
                execution_time=0.0,
                timestamp=time.time(),
                error="approval_required",
            )

        start = time.time()
        try:
            result = executor(**inputs)
            outputs = result if isinstance(result, dict) else {"result": result}
            return SkillExecutionResult(
                skill_id=skill_def.id,
                success=True,
                outputs=outputs,
                execution_time=time.time() - start,
                timestamp=time.time(),
            )
        except Exception as exc:  # pylint: disable=broad-except
            return SkillExecutionResult(
                skill_id=skill_def.id,
                success=False,
                outputs={},
                execution_time=time.time() - start,
                timestamp=time.time(),
                error=str(exc),
            )
