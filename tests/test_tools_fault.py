import unittest

from aiops.tools.fault_tools import (
    analyze_root_cause,
    assess_impact,
    diagnose_fault,
    recommend_solutions,
    validate_solution,
)


class TestFaultTools(unittest.TestCase):
    def test_diagnose_fault(self) -> None:
        result = diagnose_fault("CPU 100% usage")
        self.assertEqual(result["fault_type"], "high_cpu")

    def test_analyze_root_cause(self) -> None:
        result = analyze_root_cause({"cpu_percent": 95}, [])
        self.assertIn("CPU", result["root_cause"])

    def test_assess_impact(self) -> None:
        result = assess_impact("disk_full")
        self.assertEqual(result["severity"], "high")

    def test_recommend_solutions(self) -> None:
        result = recommend_solutions("disk full")
        self.assertTrue(result["recommendations"])

    def test_validate_solution(self) -> None:
        result = validate_solution("restart", "restart service to recover")
        self.assertEqual(result["is_valid"], "yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)

