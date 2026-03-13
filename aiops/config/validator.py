from __future__ import annotations

from typing import Callable, Iterable, Sequence
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from .settings import Settings


class ValidationIssue(BaseModel):
    path: str
    message: str


class ValidationResult(BaseModel):
    valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)

    def to_message(self) -> str:
        if self.valid:
            return "配置校验通过"
        return "; ".join(f"{issue.path}: {issue.message}" for issue in self.issues)


SettingsValidator = Callable[[Settings], Iterable[ValidationIssue]]


def _validate_http_url(value: str | None, path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if value is None or not str(value).strip():
        issues.append(ValidationIssue(path=path, message="不能为空"))
        return issues

    parsed = urlparse(str(value).strip())
    if parsed.scheme not in {"http", "https"}:
        issues.append(ValidationIssue(path=path, message="必须为 http(s) URL"))
        return issues

    if not parsed.netloc:
        issues.append(ValidationIssue(path=path, message="URL 缺少主机部分"))
        return issues

    return issues


def validate_settings(
    settings: Settings,
    extra_validators: Sequence[SettingsValidator] | None = None,
) -> ValidationResult:
    issues: list[ValidationIssue] = []

    issues.extend(_validate_http_url(settings.metrics.prometheus_base_url, "metrics.prometheus_base_url"))
    issues.extend(_validate_http_url(settings.logs.victorialogs_base_url, "logs.victorialogs_base_url"))

    if extra_validators:
        for validator in extra_validators:
            issues.extend(list(validator(settings)))

    return ValidationResult(valid=not issues, issues=issues)

