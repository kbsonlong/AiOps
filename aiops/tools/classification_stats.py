#!/usr/bin/env python3
"""
意图识别统计查询工具。

用于查看和分析意图识别的各项指标。

用法:
    # 查看统计摘要
    python -m aiops.tools.classification_stats

    # 输出 JSON 格式
    python -m aiops.tools.classification_stats --format json

    # 重置统计
    python -m aiops.tools.classification_stats --reset
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aiops.core.classification_metrics import get_metrics, IntentRecognitionMetrics


def main() -> int:
    parser = argparse.ArgumentParser(description="意图识别统计查询工具")
    parser.add_argument(
        "--format", "-f",
        choices=["summary", "json", "table"],
        default="summary",
        help="输出格式"
    )
    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="重置所有统计数据"
    )
    parser.add_argument(
        "--recent", "-n",
        type=int,
        default=0,
        help="显示最近的 N 条记录"
    )

    args = parser.parse_args()

    # 重置统计
    if args.reset:
        IntentRecognitionMetrics.reset()
        print("统计数据已重置")
        return 0

    # 获取统计
    metrics = get_metrics()
    stats = metrics.get_stats()

    # 输出
    if args.format == "summary":
        print(stats.to_summary())
    elif args.format == "json":
        print(json.dumps(stats.to_dict(), indent=2, ensure_ascii=False))
    elif args.format == "table":
        print("=" * 60)
        print(f"{'指标':<30} {'数值':>20}")
        print("=" * 60)
        print(f"{'总分类次数':<30} {stats.total_classifications:>20}")
        print("-" * 60)
        print(f"{'LLM 调用次数':<30} {stats.llm_calls_total:>20}")
        print(f"{'  - 成功':<30} {stats.llm_successes:>20}")
        print(f"{'  - 失败':<30} {stats.llm_failures:>20}")
        print(f"{'  - 成功率':<30} {stats.llm_success_rate:>19.2%}")
        print("-" * 60)
        print(f"{'Fallback 次数':<30} {stats.fallback_total:>20}")
        print(f"{'LLM 平均延迟':<30} {stats.llm_avg_latency_ms:>19.1f}ms")
        print("=" * 60)

    # 显示最近记录
    if args.recent > 0:
        print("\n最近记录:")
        records = metrics.get_recent_records(args.recent)
        for i, record in enumerate(records, 1):
            print(f"{i}. [{record.method.upper()}] {record.query[:50]}...")
            if record.source:
                print(f"   → {record.source} ({record.severity})")
            if record.error_reason:
                print(f"   ✗ {record.error_reason}")
            if record.llm_latency_ms is not None:
                print(f"   ⏱ {record.llm_latency_ms:.1f}ms")

    return 0


if __name__ == "__main__":
    sys.exit(main())
