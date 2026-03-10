import unittest

from aiops.config.security_config import SecurityConfig
from aiops.security.controller import SecurityController
from aiops.skills import SkillCategory, SkillDefinition, SkillDiscoveryService, SkillRegistry
from aiops.skills.runtime import SkillExecutionRuntime
from aiops.skills_lib import PROMETHEUS_SKILLS


class TestSkillsStage5(unittest.TestCase):
    def test_discovery_by_category(self) -> None:
        registry = SkillRegistry()
        registry.bulk_register(PROMETHEUS_SKILLS)
        discovery = SkillDiscoveryService(registry=registry)
        results = discovery.discover_skills("", category=SkillCategory.MONITORING)
        self.assertTrue(results)

    def test_runtime_requires_approval(self) -> None:
        config = SecurityConfig(approval_required=True, allowed_actions=["skill.high"])
        controller = SecurityController(config=config)
        runtime = SkillExecutionRuntime(controller)
        skill = SkillDefinition(
            id="skill.high",
            name="High Risk",
            description="high",
            category=SkillCategory.REMEDIATION,
            input_schema={},
            output_schema={},
            implementation_type="python_function",
            implementation_ref="noop",
        )

        def executor():
            return {"ok": True}

        result = runtime.execute_skill(skill, {}, executor)
        self.assertFalse(result.success)
        self.assertEqual(result.error, "approval_required")


if __name__ == "__main__":
    unittest.main(verbosity=2)
