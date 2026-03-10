from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Security and approval settings."""

    approval_required: bool = Field(default=True)
    risk_level: str = Field(default="medium")
    allowed_actions: list[str] = Field(default_factory=lambda: ["read_metrics", "read_logs"])

