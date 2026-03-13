from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, ParamSpec, TypeVar

from aiops.exceptions import AIOpsException

P = ParamSpec("P")
T = TypeVar("T")


def get_logger(name: str = "aiops") -> logging.Logger:
    return logging.getLogger(name)


def to_safe_message(exc: BaseException) -> str:
    if isinstance(exc, AIOpsException):
        return exc.safe_message
    if isinstance(exc, PermissionError):
        return "无权限执行该操作"
    if isinstance(exc, ValueError):
        return "请求参数错误"
    return "内部错误，请稍后重试"


def log_exception(
    exc: BaseException,
    *,
    operation: str,
    logger: logging.Logger | None = None,
    extra: Mapping[str, Any] | None = None,
) -> None:
    log = logger or get_logger()
    payload: dict[str, Any] = {"operation": operation, "exc_type": type(exc).__name__}
    if extra:
        payload.update(dict(extra))
    log.exception("operation_failed", extra=payload)


def safe_execute(
    func: Callable[P, T],
    *args: P.args,
    operation: str,
    fallback: T | None = None,
    on_error: Callable[[BaseException], T] | None = None,
    logger: logging.Logger | None = None,
    extra: Mapping[str, Any] | None = None,
    **kwargs: P.kwargs,
) -> T | None:
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        log_exception(exc, operation=operation, logger=logger, extra=extra)
        if on_error is not None:
            return on_error(exc)
        return fallback

