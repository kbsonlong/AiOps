from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from aiops.core.events import SkillExecutionEvent, get_event_bus
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
        bus = get_event_bus()
        decision = self.security_controller.check_action(
            action=skill_def.id,
            context={"inputs": inputs, "risk_level": skill_def.risk_level},
        )
        if not decision["allowed"]:
            result = SkillExecutionResult(
                skill_id=skill_def.id,
                success=False,
                outputs={},
                execution_time=0.0,
                timestamp=time.time(),
                error="action_not_allowed",
            )
            bus.publish_nowait(
                SkillExecutionEvent(
                    timestamp=result.timestamp,
                    source="skills.runtime",
                    skill_id=result.skill_id,
                    duration_ms=0,
                    success=False,
                    error=result.error,
                )
            )
            return result
        if decision["requires_approval"]:
            result = SkillExecutionResult(
                skill_id=skill_def.id,
                success=False,
                outputs={},
                execution_time=0.0,
                timestamp=time.time(),
                error="approval_required",
            )
            bus.publish_nowait(
                SkillExecutionEvent(
                    timestamp=result.timestamp,
                    source="skills.runtime",
                    skill_id=result.skill_id,
                    duration_ms=0,
                    success=False,
                    error=result.error,
                )
            )
            return result

        start = time.time()
        try:
            result = executor(**inputs)
            outputs = result if isinstance(result, dict) else {"result": result}
            execution_result = SkillExecutionResult(
                skill_id=skill_def.id,
                success=True,
                outputs=outputs,
                execution_time=time.time() - start,
                timestamp=time.time(),
            )
            bus.publish_nowait(
                SkillExecutionEvent(
                    timestamp=execution_result.timestamp,
                    source="skills.runtime",
                    skill_id=execution_result.skill_id,
                    duration_ms=int(execution_result.execution_time * 1000),
                    success=True,
                    error=None,
                )
            )
            return execution_result
        except Exception as exc:  # pylint: disable=broad-except
            execution_result = SkillExecutionResult(
                skill_id=skill_def.id,
                success=False,
                outputs={},
                execution_time=time.time() - start,
                timestamp=time.time(),
                error=str(exc),
            )
            bus.publish_nowait(
                SkillExecutionEvent(
                    timestamp=execution_result.timestamp,
                    source="skills.runtime",
                    skill_id=execution_result.skill_id,
                    duration_ms=int(execution_result.execution_time * 1000),
                    success=False,
                    error=execution_result.error,
                )
            )
            return execution_result
