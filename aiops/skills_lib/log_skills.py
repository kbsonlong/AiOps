from __future__ import annotations

from aiops.skills.models import SkillCategory, SkillDefinition


VICTORIALOGS_SKILLS = [
    SkillDefinition(
        id="victorialogs.query.logs",
        name="查询日志数据",
        description="使用LogSQL查询VictoriaLogs中的日志",
        category=SkillCategory.DIAGNOSIS,
        input_schema={"logql_query": "string"},
        output_schema={"raw": "object"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.logs_tools.query_victorialogs",
        tags=["victorialogs", "logs"],
    ),
]
