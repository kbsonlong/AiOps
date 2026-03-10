import unittest

from aiops.skills import (
    SkillCategory,
    SkillCompositionEngine,
    SkillDefinition,
    SkillExecutionMonitor,
    SkillExecutionRuntime,
    SkillRiskLevel,
)
from aiops.security.controller import SecurityController
from aiops.config.security_config import SecurityConfig


class TestSkillsStage2(unittest.TestCase):
    def test_composition_plan(self) -> None:
        skills = [
            SkillDefinition(
                id="skill.a",
                name="Skill A",
                description="A",
                category=SkillCategory.MONITORING,
                input_schema={},
                output_schema={},
                implementation_type="python_function",
                implementation_ref="noop",
            ),
            SkillDefinition(
                id="skill.b",
                name="Skill B",
                description="B",
                category=SkillCategory.DIAGNOSIS,
                input_schema={},
                output_schema={},
                implementation_type="python_function",
                implementation_ref="noop",
            ),
        ]
        engine = SkillCompositionEngine()
        plan = engine.build_execution_plan(skills, context={"x": 1})
        self.assertEqual(len(plan.execution_order), 2)
        self.assertEqual(plan.context["x"], 1)

    def test_runtime_security(self) -> None:
        config = SecurityConfig(approval_required=False, allowed_actions=["skill.exec"])
        controller = SecurityController(config=config)
        runtime = SkillExecutionRuntime(controller)
        skill = SkillDefinition(
            id="skill.exec",
            name="Exec",
            description="exec",
            category=SkillCategory.MONITORING,
            input_schema={"value": "int"},
            output_schema={"value": "int"},
            implementation_type="python_function",
            implementation_ref="noop",
            risk_level=SkillRiskLevel.LOW,
        )

        def executor(value: int):
            return {"value": value + 1}

        result = runtime.execute_skill(skill, {"value": 1}, executor)
        self.assertTrue(result.success)
        self.assertEqual(result.outputs["value"], 2)

    def test_monitoring_stats(self) -> None:
        monitor = SkillExecutionMonitor()
        self.assertEqual(monitor.success_rate(), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

