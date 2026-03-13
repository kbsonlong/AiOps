from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import aiohttp

from aiops.config import load_settings
from aiops.config.validator import validate_settings


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True)
class CheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    detail: str = ""
    response_time_ms: int = 0
    issues: list[str] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "response_time_ms": self.response_time_ms,
            "issues": self.issues or [],
        }


def _now_iso() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class HealthChecker:
    """Health checker for system components."""

    def __init__(self):
        self._timeout = 5  # seconds

    async def check_prometheus(self, base_url: str) -> CheckResult:
        """Check Prometheus connectivity."""
        start_time = time.time()
        try:
            health_url = f"{base_url.rstrip('/')}/-/healthy"
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=self._timeout) as resp:
                    response_time = int((time.time() - start_time) * 1000)
                    if resp.status == 200:
                        return CheckResult(
                            name="prometheus",
                            status=HealthStatus.HEALTHY,
                            detail="Prometheus is healthy",
                            response_time_ms=response_time,
                        )
                    return CheckResult(
                        name="prometheus",
                        status=HealthStatus.UNHEALTHY,
                        detail=f"Prometheus returned status {resp.status}",
                        response_time_ms=response_time,
                    )
        except asyncio.TimeoutError:
            return CheckResult(
                name="prometheus",
                status=HealthStatus.UNHEALTHY,
                detail="Connection timeout",
                response_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return CheckResult(
                name="prometheus",
                status=HealthStatus.UNHEALTHY,
                detail=str(e),
                response_time_ms=int((time.time() - start_time) * 1000),
            )

    async def check_victorialogs(self, base_url: str) -> CheckResult:
        """Check VictoriaLogs connectivity."""
        start_time = time.time()
        try:
            health_url = f"{base_url.rstrip('/')}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=self._timeout) as resp:
                    response_time = int((time.time() - start_time) * 1000)
                    if resp.status == 200:
                        return CheckResult(
                            name="victorialogs",
                            status=HealthStatus.HEALTHY,
                            detail="VictoriaLogs is healthy",
                            response_time_ms=response_time,
                        )
                    return CheckResult(
                        name="victorialogs",
                        status=HealthStatus.UNHEALTHY,
                        detail=f"VictoriaLogs returned status {resp.status}",
                        response_time_ms=response_time,
                    )
        except asyncio.TimeoutError:
            return CheckResult(
                name="victorialogs",
                status=HealthStatus.UNHEALTHY,
                detail="Connection timeout",
                response_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            return CheckResult(
                name="victorialogs",
                status=HealthStatus.UNHEALTHY,
                detail=str(e),
                response_time_ms=int((time.time() - start_time) * 1000),
            )

    def check_config(self) -> CheckResult:
        """Check configuration validity."""
        start_time = time.time()
        try:
            settings = load_settings()
            result = validate_settings(settings)
            response_time = int((time.time() - start_time) * 1000)
            if result.valid:
                return CheckResult(
                    name="config",
                    status=HealthStatus.HEALTHY,
                    detail="Configuration is valid",
                    response_time_ms=response_time,
                )
            return CheckResult(
                name="config",
                status=HealthStatus.UNHEALTHY,
                detail="Configuration validation failed",
                response_time_ms=response_time,
                issues=[f"{issue.path}: {issue.message}" for issue in result.issues],
            )
        except Exception as e:
            return CheckResult(
                name="config",
                status=HealthStatus.UNHEALTHY,
                detail=str(e),
                response_time_ms=int((time.time() - start_time) * 1000),
            )

    async def check_all(self, include_services: bool = True) -> dict[str, CheckResult]:
        """Run all health checks."""
        checks: dict[str, CheckResult] = {}
        checks["config"] = self.check_config()

        if include_services:
            try:
                settings = load_settings()
                # Run service checks in parallel
                service_checks = []
                if settings.metrics.prometheus_base_url:
                    service_checks.append(self.check_prometheus(settings.metrics.prometheus_base_url))
                if settings.logs.victorialogs_base_url:
                    service_checks.append(self.check_victorialogs(settings.logs.victorialogs_base_url))

                if service_checks:
                    results = await asyncio.gather(*service_checks, return_exceptions=True)
                    for result in results:
                        if isinstance(result, CheckResult):
                            checks[result.name] = result
            except Exception:
                pass  # Service checks are optional

        return checks


async def build_health_report(include_services: bool = True) -> dict:
    """Build comprehensive health report."""
    checker = HealthChecker()
    checks = await checker.check_all(include_services=include_services)

    # Determine overall status
    overall_status = HealthStatus.HEALTHY
    for check in checks.values():
        if check.status == HealthStatus.UNHEALTHY:
            overall_status = HealthStatus.UNHEALTHY
            break
        elif check.status == HealthStatus.DEGRADED:
            overall_status = HealthStatus.DEGRADED

    return {
        "status": overall_status.value,
        "timestamp": _now_iso(),
        "checks": {name: check.to_dict() for name, check in checks.items()},
    }


def build_health_report_sync() -> dict:
    """Synchronous wrapper for health report building."""
    return asyncio.run(build_health_report())
