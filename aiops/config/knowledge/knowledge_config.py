from __future__ import annotations

from pydantic import BaseModel, Field

from .embeddings_config import EmbeddingsConfig
from .vector_store_config import VectorStoreConfig


class KnowledgeConfig(BaseModel):
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)

