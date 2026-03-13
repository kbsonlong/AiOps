"""Core utilities for AIOps."""

from aiops.core.container import (
    Container,
    get_global_container,
    reset_global_container,
)
from aiops.core.error_handler import (
    get_logger,
    log_exception,
    safe_execute,
)
from aiops.core.events import EventBus, Event
from aiops.core.http_pool import (
    HTTPConnectionPool,
    ServiceHTTPClient,
    get_http_client,
    close_http_client,
)

__all__ = [
    # Dependency injection
    "Container",
    "get_global_container",
    "reset_global_container",
    # Error handling
    "get_logger",
    "log_exception",
    "safe_execute",
    # Events
    "EventBus",
    "Event",
    # HTTP
    "HTTPConnectionPool",
    "ServiceHTTPClient",
    "get_http_client",
    "close_http_client",
]
