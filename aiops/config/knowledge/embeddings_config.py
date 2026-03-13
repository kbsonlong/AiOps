from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EmbeddingsConfig(BaseModel):
    model: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    api_base: Optional[str] = Field(default=None)

