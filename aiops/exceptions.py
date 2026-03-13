from __future__ import annotations

from dataclasses import dataclass


@dataclass(eq=False)
class AIOpsException(Exception):
    message: str
    safe_message: str = "操作失败"
    error_code: str = "aiops_error"

    def __str__(self) -> str:
        return self.message


class ConfigException(AIOpsException):
    def __init__(
        self,
        message: str,
        safe_message: str = "配置错误",
        error_code: str = "config_error",
    ) -> None:
        super().__init__(message=message, safe_message=safe_message, error_code=error_code)


class WorkflowException(AIOpsException):
    def __init__(
        self,
        message: str,
        safe_message: str = "工作流执行失败",
        error_code: str = "workflow_error",
    ) -> None:
        super().__init__(message=message, safe_message=safe_message, error_code=error_code)


class SkillException(AIOpsException):
    def __init__(
        self,
        message: str,
        safe_message: str = "技能处理失败",
        error_code: str = "skill_error",
    ) -> None:
        super().__init__(message=message, safe_message=safe_message, error_code=error_code)


class AgentException(AIOpsException):
    def __init__(
        self,
        message: str,
        safe_message: str = "代理执行失败",
        error_code: str = "agent_error",
    ) -> None:
        super().__init__(message=message, safe_message=safe_message, error_code=error_code)

