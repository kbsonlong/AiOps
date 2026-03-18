"""意图识别统计追踪模块。

用于跟踪意图识别过程中的各项指标，包括：
- LLM 调用次数
- LLM 成功次数
- LLM 失败次数 (导致 fallback)
- Fallback 触发次数
- 分类结果分布
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal


Source = Literal["metrics", "logs", "fault", "security", "knowledge_base"]
Severity = Literal["low", "medium", "high", "critical"]


@dataclass
class ClassificationRecord:
    """单次分类记录。"""
    timestamp: float
    query: str
    method: Literal["llm", "fallback"]
    source: Source | None
    severity: Severity | None
    llm_latency_ms: float | None = None
    error_reason: str | None = None


class IntentRecognitionMetrics:
    """意图识别统计追踪器。

    线程安全的单例模式，用于记录和查询意图识别的各项指标。

    使用示例:
        metrics = IntentRecognitionMetrics.get_instance()

        # 记录 LLM 调用
        with metrics.track_llm_call():
            result = router_llm.invoke(prompt)

        # 记录成功分类
        metrics.record_success(query, source, severity)

        # 记录 fallback
        metrics.record_fallback(query, error_reason)

        # 获取统计
        stats = metrics.get_stats()
        print(stats.to_summary())
    """

    _instance: IntentRecognitionMetrics | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """初始化追踪器（单例模式）。"""
        self._records: list[ClassificationRecord] = []
        self._llm_calls_total = 0
        self._llm_successes = 0
        self._llm_failures = 0
        self._fallback_total = 0
        self._source_distribution: Counter[Source] = Counter()
        self._severity_distribution: Counter[Severity] = Counter()
        self._llm_latency_total_ms = 0.0

    @classmethod
    def get_instance(cls) -> IntentRecognitionMetrics:
        """获取单例实例。"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置所有统计（主要用于测试）。"""
        with cls._lock:
            cls._instance = None

    def track_llm_call(self):
        """跟踪 LLM 调用的上下文管理器。

        自动记录调用次数和延迟。

        用法:
            with metrics.track_llm_call() as tracker:
                result = llm.invoke(prompt)
                tracker.set_success()

            # 或在 try-except 中:
            try:
                with metrics.track_llm_call():
                    result = llm.invoke(prompt)
            except Exception as e:
                metrics.record_llm_failure(str(e))
        """
        return _LLMCallTracker(self)

    def _record_llm_call_start(self) -> float:
        """记录 LLM 调用开始。"""
        with self._lock:
            self._llm_calls_total += 1
        return time.perf_counter()

    def _record_llm_call_end(self, start_time: float, success: bool = True):
        """记录 LLM 调用结束。"""
        latency_ms = (time.perf_counter() - start_time) * 1000
        with self._lock:
            if success:
                self._llm_successes += 1
            else:
                self._llm_failures += 1
            self._llm_latency_total_ms += latency_ms

    def record_success(
        self,
        query: str,
        source: Source,
        severity: Severity,
        method: Literal["llm", "fallback"],
        llm_latency_ms: float | None = None,
    ) -> None:
        """记录成功的分类。"""
        with self._lock:
            self._source_distribution[source] += 1
            self._severity_distribution[severity] += 1
            self._records.append(ClassificationRecord(
                timestamp=time.time(),
                query=query,
                method=method,
                source=source,
                severity=severity,
                llm_latency_ms=llm_latency_ms,
            ))

    def record_fallback(self, query: str, error_reason: str | None = None) -> None:
        """记录 fallback 触发。"""
        with self._lock:
            self._fallback_total += 1
            self._records.append(ClassificationRecord(
                timestamp=time.time(),
                query=query,
                method="fallback",
                source=None,
                severity=None,
                error_reason=error_reason,
            ))

    def get_stats(self) -> "ClassificationStats":
        """获取当前统计信息。"""
        with self._lock:
            return ClassificationStats(
                llm_calls_total=self._llm_calls_total,
                llm_successes=self._llm_successes,
                llm_failures=self._llm_failures,
                fallback_total=self._fallback_total,
                llm_success_rate=(
                    self._llm_successes / self._llm_calls_total
                    if self._llm_calls_total > 0 else 0.0
                ),
                source_distribution=dict(self._source_distribution),
                severity_distribution=dict(self._severity_distribution),
                llm_avg_latency_ms=(
                    self._llm_latency_total_ms / self._llm_successes
                    if self._llm_successes > 0 else 0.0
                ),
                total_classifications=len(self._records),
            )

    def get_recent_records(self, limit: int = 100) -> list[ClassificationRecord]:
        """获取最近的分类记录。"""
        with self._lock:
            return self._records[-limit:]


class _LLMCallTracker:
    """LLM 调用跟踪器内部类。"""

    def __init__(self, metrics: IntentRecognitionMetrics):
        self._metrics = metrics
        self._start_time: float | None = None

    def __enter__(self):
        self._start_time = self._metrics._record_llm_call_start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start_time is not None:
            success = exc_type is None
            self._metrics._record_llm_call_end(self._start_time, success)


@dataclass
class ClassificationStats:
    """分类统计信息。"""
    llm_calls_total: int
    llm_successes: int
    llm_failures: int
    fallback_total: int
    llm_success_rate: float
    source_distribution: dict[Source, int]
    severity_distribution: dict[Severity, int]
    llm_avg_latency_ms: float
    total_classifications: int

    def to_summary(self) -> str:
        """生成统计摘要字符串。"""
        lines = [
            "=" * 50,
            "意图识别统计摘要",
            "=" * 50,
            f"总分类次数: {self.total_classifications}",
            f"LLM 调用次数: {self.llm_calls_total}",
            f"  - 成功: {self.llm_successes}",
            f"  - 失败: {self.llm_failures}",
            f"  - 成功率: {self.llm_success_rate:.1%}",
            f"Fallback 次数: {self.fallback_total}",
            f"LLM 平均延迟: {self.llm_avg_latency_ms:.1f}ms",
            "",
            "分类源分布:",
        ]
        for source, count in sorted(self.source_distribution.items(), key=lambda x: -x[1]):
            pct = count / self.total_classifications * 100 if self.total_classifications > 0 else 0
            lines.append(f"  - {source}: {count} ({pct:.1f}%)")

        lines.extend([
            "",
            "严重程度分布:",
        ])
        for severity, count in sorted(self.severity_distribution.items(), key=lambda x: -x[1]):
            pct = count / self.total_classifications * 100 if self.total_classifications > 0 else 0
            lines.append(f"  - {severity}: {count} ({pct:.1f}%)")

        lines.append("=" * 50)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """转换为字典格式。"""
        return {
            "total_classifications": self.total_classifications,
            "llm": {
                "calls_total": self.llm_calls_total,
                "successes": self.llm_successes,
                "failures": self.llm_failures,
                "success_rate": round(self.llm_success_rate, 4),
                "avg_latency_ms": round(self.llm_avg_latency_ms, 2),
            },
            "fallback": {
                "total": self.fallback_total,
            },
            "distribution": {
                "by_source": self.source_distribution,
                "by_severity": self.severity_distribution,
            },
        }


def get_metrics() -> IntentRecognitionMetrics:
    """获取意图识别统计追踪器实例。"""
    return IntentRecognitionMetrics.get_instance()
