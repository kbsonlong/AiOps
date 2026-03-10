from __future__ import annotations

from aiops.skills.models import SkillCategory, SkillDefinition, SkillRiskLevel


SECURITY_SKILLS = [
    SkillDefinition(
        id="security.scan.vulnerabilities",
        name="扫描漏洞",
        description="扫描系统中的安全漏洞",
        category=SkillCategory.SECURITY,
        risk_level=SkillRiskLevel.MEDIUM,
        input_schema={"target": "string"},
        output_schema={"status": "string"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.security_tools.scan_vulnerabilities",
        tags=["security", "scan"],
    ),
    SkillDefinition(
        id="security.audit.config",
        name="审计安全配置",
        description="审计系统的安全配置合规性",
        category=SkillCategory.SECURITY,
        input_schema={"config_type": "string"},
        output_schema={"status": "string"},
        implementation_type="python_function",
        implementation_ref="aiops.tools.security_tools.check_security_config",
        tags=["security", "audit"],
    ),
]
