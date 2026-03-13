"""Health check API endpoints.

This module provides FastAPI endpoints for health monitoring,
including liveness and readiness probes for Kubernetes.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from aiops.health import (
    HealthChecker,
    HealthStatus,
    build_health_report,
    build_health_report_sync,
)


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


def reset_health_checker() -> None:
    """Reset the global health checker (for testing)."""
    global _health_checker
    _health_checker = None


# Create router
router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
@router.get("/")
async def health_check(include_services: bool = True) -> dict:
    """Comprehensive health check endpoint.

    Args:
        include_services: Whether to include external service checks (default: True)

    Returns:
        Health check report with overall status and individual component status

    Example response:
        ```json
        {
            "status": "healthy",
            "timestamp": "2026-03-13T12:00:00Z",
            "checks": {
                "config": {
                    "name": "config",
                    "status": "healthy",
                    "detail": "Configuration is valid",
                    "response_time_ms": 5
                },
                "prometheus": {
                    "name": "prometheus",
                    "status": "healthy",
                    "detail": "Prometheus is healthy",
                    "response_time_ms": 12
                }
            }
        }
        ```
    """
    try:
        return await build_health_report(include_services=include_services)
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": None,
            "checks": {},
            "error": str(e),
        }


@router.get("/live")
async def liveness_probe() -> dict:
    """Liveness probe for Kubernetes.

    This endpoint checks if the application is running.
    It always returns 200 if the service is alive.

    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": None,
    }


@router.get("/ready")
async def readiness_probe() -> dict:
    """Readiness probe for Kubernetes.

    This endpoint checks if the application is ready to serve requests.
    It returns 503 if the configuration is invalid.

    Returns:
        Readiness status

    Raises:
        HTTPException: If the service is not ready (503)
    """
    checker = get_health_checker()
    config_check = checker.check_config()

    if config_check.status != HealthStatus.HEALTHY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "reason": config_check.detail,
                "issues": config_check.issues or [],
            },
        )

    return {
        "status": "ready",
        "timestamp": None,
    }


@router.get("/config")
async def config_check() -> dict:
    """Configuration-only health check.

    This endpoint checks only the configuration validity,
    without checking external services.

    Returns:
        Configuration check result
    """
    checker = get_health_checker()
    result = checker.check_config()
    return result.to_dict()


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastAPI app.

    This is used to initialize and cleanup resources.
    """
    # Startup
    global _health_checker
    _health_checker = HealthChecker()
    yield
    # Shutdown
    _health_checker = None
