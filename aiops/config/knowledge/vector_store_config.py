from __future__ import annotations

from pydantic import BaseModel, Field


class VectorStoreConfig(BaseModel):
    persist_directory: str = Field(default="./chroma_db")
    collection_name: str = Field(default="knowledge_base")

