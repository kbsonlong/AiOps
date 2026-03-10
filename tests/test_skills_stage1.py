import unittest

from aiops.skills import SkillCategory, SkillDefinition, SkillDiscoveryService, SkillRegistry


class TestSkillStage1(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = SkillRegistry()
        self.discovery = SkillDiscoveryService(registry=self.registry)
        self.skill = SkillDefinition(
            id="prometheus.query.cpu",
            name="查询CPU指标",
            description="查询Prometheus中的CPU相关指标",
            category=SkillCategory.MONITORING,
            input_schema={"query": "string"},
            output_schema={"value": "float"},
            implementation_type="python_function",
            implementation_ref="aiops.tools.metrics_tools.query_prometheus",
            tags=["prometheus", "cpu"],
        )
        self.registry.register(self.skill)

    def test_registry_get(self) -> None:
        fetched = self.registry.get("prometheus.query.cpu")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "查询CPU指标")

    def test_discovery(self) -> None:
        results = self.discovery.discover_skills("cpu")
        self.assertEqual(len(results), 1)
        results_tag = self.discovery.discover_skills("query", tags=["prometheus"])
        self.assertEqual(len(results_tag), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

