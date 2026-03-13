import unittest

from aiops.skills.metrics import SkillMetrics


class TestSkillMetrics(unittest.TestCase):
    def test_record_metrics(self) -> None:
        metrics = SkillMetrics()
        metrics.record(success=True, execution_time=1.2)
        metrics.record(success=False, execution_time=0.8)
        data = metrics.to_dict()
        self.assertEqual(data["executions"], 2.0)
        self.assertEqual(data["successes"], 1.0)
        self.assertEqual(data["failures"], 1.0)
        self.assertGreater(data["avg_execution_time"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
