from __future__ import annotations

from aiops.skills.models import SkillCategory, SkillDefinition, SkillRiskLevel


FAULT_DIAGNOSIS_SKILLS = [
    SkillDefinition(
        id="diagnose.root.cause",
        name="诊断根本原因",
        description="基于指标和日志数据诊断系统故障的根本原因",
        category=SkillCategory.DIAGNOSIS,
        input_schema={"metrics": "dict", "logs": "list"},
        output_schema={"root_cause": "string"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.fault_tools.analyze_root_cause",
        tags=["fault", "diagnosis"],
    ),
    SkillDefinition(
        id="recommend.solution",
        name="推荐解决方案",
        description="为诊断出的问题推荐解决方案",
        category=SkillCategory.REMEDIATION,
        risk_level=SkillRiskLevel.HIGH,
        input_schema={"fault_analysis": "string"},
        output_schema={"recommendations": "list"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.fault_tools.recommend_solutions",
        tags=["remediation"],
    ),
]
