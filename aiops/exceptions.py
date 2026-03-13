"""AIOps exception hierarchy.

This module defines a unified exception hierarchy for the AIOps system,
providing consistent error handling and reporting across all components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class AIOpsException(Exception):
    """Base exception for all AIOps errors.

    Attributes:
        message: The detailed error message (may contain sensitive information)
        safe_message: A user-safe message without sensitive details
        error_code: Unique error code for this exception type
        details: Additional error context (optional)
    """
    message: str
    safe_message: str = "操作失败"
    error_code: str = "aiops_error"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigException(AIOpsException):
    """Base exception for configuration errors."""

    def __init__(
        self,
        message: str,
        safe_message: str = "配置错误",
        error_code: str = "config_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            safe_message=safe_message,
            error_code=error_code,
            details=details or {},
        )


class ConfigValidationError(ConfigException):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        validation_errors: list[str] | None = None,
        **kwargs
    ) -> None:
        details = {"validation_errors": validation_errors or []}
        super().__init__(
            message=message,
            safe_message="配置验证失败",
            error_code="config_validation_error",
            details=details,
            **kwargs
        )


class ConfigLoadError(ConfigException):
    """Raised when configuration cannot be loaded."""

    def __init__(
        self,
        message: str,
        config_path: str | None = None,
        **kwargs
    ) -> None:
        details = {}
        if config_path:
            details["config_path"] = config_path
        super().__init__(
            message=message,
            safe_message="无法加载配置",
            error_code="config_load_error",
            details=details,
            **kwargs
        )


# ============================================================================
# Workflow Exceptions
# ============================================================================

class WorkflowException(AIOpsException):
    """Base exception for workflow errors."""

    def __init__(
        self,
        message: str,
        safe_message: str = "工作流执行失败",
        error_code: str = "workflow_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            safe_message=safe_message,
            error_code=error_code,
            details=details or {},
        )


class WorkflowExecutionError(WorkflowException):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        message: str,
        workflow_name: str | None = None,
        node_name: str | None = None,
        **kwargs
    ) -> None:
        details = {}
        if workflow_name:
            details["workflow_name"] = workflow_name
        if node_name:
            details["node_name"] = node_name
        super().__init__(
            message=message,
            safe_message="工作流执行失败",
            error_code="workflow_execution_error",
            details=details,
            **kwargs
        )


class WorkflowStateError(WorkflowException):
    """Raised when workflow state is invalid."""

    def __init__(
        self,
        message: str,
        state_key: str | None = None,
        **kwargs
    ) -> None:
        details = {"state_key": state_key} if state_key else {}
        super().__init__(
            message=message,
            safe_message="工作流状态错误",
            error_code="workflow_state_error",
            details=details,
            **kwargs
        )


# ============================================================================
# Skill Exceptions
# ============================================================================

class SkillException(AIOpsException):
    """Base exception for skill-related errors."""

    def __init__(
        self,
        message: str,
        safe_message: str = "技能处理失败",
        error_code: str = "skill_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            safe_message=safe_message,
            error_code=error_code,
            details=details or {},
        )


class SkillNotFoundError(SkillException):
    """Raised when a skill is not found."""

    def __init__(
        self,
        skill_id: str,
        **kwargs
    ) -> None:
        super().__init__(
            message=f"Skill not found: {skill_id}",
            safe_message=f"技能不存在: {skill_id}",
            error_code="skill_not_found",
            details={"skill_id": skill_id},
            **kwargs
        )


class SkillExecutionError(SkillException):
    """Raised when skill execution fails."""

    def __init__(
        self,
        message: str,
        skill_id: str | None = None,
        execution_time_ms: int | None = None,
        **kwargs
    ) -> None:
        details = {}
        if skill_id:
            details["skill_id"] = skill_id
        if execution_time_ms is not None:
            details["execution_time_ms"] = execution_time_ms
        super().__init__(
            message=message,
            safe_message="技能执行失败",
            error_code="skill_execution_error",
            details=details,
            **kwargs
        )


class SkillValidationError(SkillException):
    """Raised when skill validation fails."""

    def __init__(
        self,
        message: str,
        skill_id: str | None = None,
        validation_errors: list[str] | None = None,
        **kwargs
    ) -> None:
        details = {}
        if skill_id:
            details["skill_id"] = skill_id
        if validation_errors:
            details["validation_errors"] = validation_errors
        super().__init__(
            message=message,
            safe_message="技能验证失败",
            error_code="skill_validation_error",
            details=details,
            **kwargs
        )


class SandboxSecurityError(SkillException):
    """Raised when sandbox security is violated."""

    def __init__(
        self,
        message: str,
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            safe_message="沙箱安全错误",
            error_code="sandbox_security_error",
            **kwargs
        )


# ============================================================================
# Agent Exceptions
# ============================================================================

class AgentException(AIOpsException):
    """Base exception for agent-related errors."""

    def __init__(
        self,
        message: str,
        safe_message: str = "代理执行失败",
        error_code: str = "agent_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            safe_message=safe_message,
            error_code=error_code,
            details=details or {},
        )


class AgentExecutionError(AgentException):
    """Raised when agent execution fails."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        **kwargs
    ) -> None:
        details = {"agent_name": agent_name} if agent_name else {}
        super().__init__(
            message=message,
            safe_message="代理执行失败",
            error_code="agent_execution_error",
            details=details,
            **kwargs
        )


class AgentTimeoutError(AgentException):
    """Raised when agent execution times out."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        timeout_seconds: int | None = None,
        **kwargs
    ) -> None:
        details = {}
        if agent_name:
            details["agent_name"] = agent_name
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            safe_message="代理执行超时",
            error_code="agent_timeout_error",
            details=details,
            **kwargs
        )


class AgentResponseError(AgentException):
    """Raised when agent response is invalid."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        response_text: str | None = None,
        **kwargs
    ) -> None:
        details = {}
        if agent_name:
            details["agent_name"] = agent_name
        if response_text:
            details["response_preview"] = response_text[:200]
        super().__init__(
            message=message,
            safe_message="代理响应错误",
            error_code="agent_response_error",
            details=details,
            **kwargs
        )


# ============================================================================
# Knowledge Base Exceptions
# ============================================================================

class KnowledgeException(AIOpsException):
    """Base exception for knowledge base errors."""

    def __init__(
        self,
        message: str,
        safe_message: str = "知识库错误",
        error_code: str = "knowledge_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            safe_message=safe_message,
            error_code=error_code,
            details=details or {},
        )


class VectorStoreError(KnowledgeException):
    """Raised when vector store operation fails."""

    def __init__(
        self,
        message: str,
        collection_name: str | None = None,
        **kwargs
    ) -> None:
        details = {"collection_name": collection_name} if collection_name else {}
        super().__init__(
            message=message,
            safe_message="向量存储错误",
            error_code="vector_store_error",
            details=details,
            **kwargs
        )


class EmbeddingError(KnowledgeException):
    """Raised when embedding generation fails."""

    def __init__(
        self,
        message: str,
        **kwargs
    ) -> None:
        super().__init__(
            message=message,
            safe_message="嵌入生成错误",
            error_code="embedding_error",
            **kwargs
        )


# ============================================================================
# External Service Exceptions
# ============================================================================

class ExternalServiceException(AIOpsException):
    """Base exception for external service errors."""

    def __init__(
        self,
        message: str,
        safe_message: str = "外部服务错误",
        error_code: str = "external_service_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            safe_message=safe_message,
            error_code=error_code,
            details=details or {},
        )


class ServiceConnectionError(ExternalServiceException):
    """Raised when connection to external service fails."""

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        **kwargs
    ) -> None:
        details = {"service_name": service_name} if service_name else {}
        super().__init__(
            message=message,
            safe_message="服务连接失败",
            error_code="service_connection_error",
            details=details,
            **kwargs
        )


class ServiceTimeoutError(ExternalServiceException):
    """Raised when external service request times out."""

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        timeout_seconds: int | None = None,
        **kwargs
    ) -> None:
        details = {}
        if service_name:
            details["service_name"] = service_name
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message=message,
            safe_message="服务请求超时",
            error_code="service_timeout_error",
            details=details,
            **kwargs
        )

