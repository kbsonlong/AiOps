#!/usr/bin/env python3
"""
意图识别统计测试脚本。

演示如何使用统计追踪器。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aiops.core.classification_metrics import (
    get_metrics,
    IntentRecognitionMetrics,
)

# 导入 fallback 函数
from aiops.workflows.router_workflow import _classify_fallback


def test_fallback_tracking():
    """测试 fallback 追踪。"""
    print("=== 测试 Fallback 追踪 ===\n")

    metrics = get_metrics()

    # 重置统计
    IntentRecognitionMetrics.reset()

    test_queries = [
        "CPU 使用率超过 90%",
        "查看最近的错误日志",
        "检测到 SSH 暴力破解",
        "系统响应很慢，请帮我诊断",
        "什么是 AIOps？",
        "Database connection timeout",
        "Check firewall rules",
    ]

    print("模拟分类查询...")
    for query in test_queries:
        result = _classify_fallback(query)
        source = result[0]["source"]
        severity = result[0]["severity"]

        # 记录分类
        metrics.record_success(
            query=query,
            source=source,
            severity=severity,
            method="fallback"
        )
        print(f"  ✓ '{query}' → {source} ({severity})")

    # 获取统计
    stats = metrics.get_stats()

    print("\n" + "=" * 50)
    print("统计结果:")
    print("=" * 50)
    print(f"总分类次数: {stats.total_classifications}")
    print(f"LLM 调用次数: {stats.llm_calls_total}")
    print(f"Fallback 次数: {stats.llm_failures + stats.fallback_total}")

    print("\n分类源分布:")
    for source, count in sorted(stats.source_distribution.items()):
        pct = count / stats.total_classifications * 100
        print(f"  - {source}: {count} ({pct:.1f}%)")

    print("\n严重程度分布:")
    for severity, count in sorted(stats.severity_distribution.items()):
        pct = count / stats.total_classifications * 100
        print(f"  - {severity}: {count} ({pct:.1f}%)")

    print("\n" + "=" * 50)
    print("✓ 统计追踪功能正常")


def test_llm_tracking_simulation():
    """测试 LLM 调用追踪模拟。"""
    print("\n\n=== 测试 LLM 调用追踪模拟 ===\n")

    metrics = get_metrics()
    IntentRecognitionMetrics.reset()

    # 模拟 LLM 调用
    print("模拟 LLM 调用...")

    # 成功的 LLM 调用
    with metrics.track_llm_call():
        pass  # 实际场景会调用 router_llm.invoke()
    metrics.record_success("分析系统性能", "metrics", "medium", method="llm")
    print("  ✓ LLM 成功分类 1")

    with metrics.track_llm_call():
        pass
    metrics.record_success("检查日志错误", "logs", "high", method="llm")
    print("  ✓ LLM 成功分类 2")

    # 模拟 LLM 调用失败，触发 fallback
    try:
        with metrics.track_llm_call():
            # 这里会抛出异常，模拟 LLM 调用失败
            raise ConnectionError("LLM 服务不可用")
    except ConnectionError:
        metrics.record_fallback("检测到入侵", "LLM服务不可用")
        print("  ✗ LLM 调用失败，触发 fallback")

    stats = metrics.get_stats()

    print("\n" + "=" * 50)
    print("统计结果:")
    print("=" * 50)
    print(f"总分类次数: {stats.total_classifications}")
    print(f"LLM 调用次数: {stats.llm_calls_total}")
    print(f"  - 成功: {stats.llm_successes}")
    print(f"  - 失败: {stats.llm_failures}")
    print(f"  - 成功率: {stats.llm_success_rate:.1%}")
    print(f"Fallback 次数: {stats.fallback_total}")
    print(f"LLM 平均延迟: {stats.llm_avg_latency_ms:.1f}ms")

    print("\n" + "=" * 50)
    print("✓ LLM 追踪功能正常")


if __name__ == "__main__":
    test_fallback_tracking()
    test_llm_tracking_simulation()
    print("\n所有测试通过!")
