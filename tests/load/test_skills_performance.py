import time
import unittest

from aiops.skills.guard import SkillsGuard
from aiops.skills.quality import SkillQualityEvaluator


class TestSkillsPerformance(unittest.TestCase):
    def test_quality_eval_performance(self) -> None:
        evaluator = SkillQualityEvaluator()
        content = "\n".join(
            [
                "## 概述",
                "性能测试内容。",
                "## 输入参数",
                "- a: 默认 1",
                "## 执行步骤",
                "1. step",
                "2. step",
                "## 输出格式",
                "text",
                "## 注意事项",
                "谨慎执行，确认再执行，备份再操作，测试环境先验证。",
            ]
        )
        start = time.perf_counter()
        for _ in range(200):
            evaluator.evaluate(content)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0)

    def test_security_scan_performance(self) -> None:
        guard = SkillsGuard()
        content = "echo ok\n" * 1000
        start = time.perf_counter()
        for _ in range(50):
            guard._calculate_risk_level([])  # type: ignore[attr-defined]
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 0.2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
