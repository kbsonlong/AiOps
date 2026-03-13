from pydantic import BaseModel, Field


class CacheConfig(BaseModel):
    enabled: bool = Field(default=True)
    default_ttl_sec: float | None = Field(default=60.0)
    max_entries: int = Field(default=2048, ge=1)
