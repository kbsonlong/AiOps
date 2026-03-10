from __future__ import annotations

from aiops.skills.models import SkillCategory, SkillDefinition


PROMETHEUS_SKILLS = [
    SkillDefinition(
        id="prometheus.query.cpu",
        name="查询CPU指标",
        description="查询Prometheus中的CPU相关指标",
        category=SkillCategory.MONITORING,
        input_schema={"query": "string"},
        output_schema={"raw": "object"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.metrics_tools.query_prometheus",
        tags=["prometheus", "cpu"],
    ),
    SkillDefinition(
        id="prometheus.query.memory",
        name="查询内存指标",
        description="查询Prometheus中的内存使用情况",
        category=SkillCategory.MONITORING,
        input_schema={"query": "string"},
        output_schema={"raw": "object"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.metrics_tools.query_prometheus",
        tags=["prometheus", "memory"],
    ),
]
