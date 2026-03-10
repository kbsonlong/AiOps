from pydantic import BaseModel, Field


class LogsConfig(BaseModel):
    """Log collection and analysis options."""

    log_type: str = Field(default="syslog")
    max_lines: int = Field(default=200, ge=10, le=10000)
    anomaly_window: int = Field(default=200, ge=10, le=10000)
    include_application_logs: bool = Field(default=True)
    victorialogs_base_url: str = Field(default="http://localhost:9428")
    victorialogs_query_path: str = Field(default="/select/logsql/query")
    otel_logs_query_url: str = Field(
        default="http://localhost:4318",
        description="OTel logs query endpoint exposed by log backend gateway",
    )
    query_timeout_sec: float = Field(default=5.0, gt=0.0)
