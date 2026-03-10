from pydantic import BaseModel, Field


class MetricsConfig(BaseModel):
    """Metrics collection thresholds and options."""

    cpu_threshold: float = Field(default=80.0, ge=0.0, le=100.0)
    memory_threshold: float = Field(default=80.0, ge=0.0, le=100.0)
    disk_threshold: float = Field(default=80.0, ge=0.0, le=100.0)
    sample_interval_sec: float = Field(default=1.0, gt=0.0)
    include_process_metrics: bool = Field(default=True)
    prometheus_base_url: str = Field(default="http://localhost:9090")
    otel_metrics_query_url: str = Field(
        default="http://localhost:8889",
        description="Prometheus-compatible query endpoint exposed by OTel stack",
    )
    query_timeout_sec: float = Field(default=5.0, gt=0.0)
