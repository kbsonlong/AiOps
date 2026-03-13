import os
import litellm
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_litellm import LiteLLMEmbeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from aiops.config.settings import Settings

class SafeLiteLLMEmbeddings(LiteLLMEmbeddings):
    """
    A wrapper around LiteLLMEmbeddings that ensures global litellm configuration
    doesn't interfere with the embedding call.
    """
    def embed_query(self, text: str) -> List[float]:
        original_base = getattr(litellm, "api_base", None)
        try:
            if self.api_base:
                litellm.api_base = None
            return super().embed_query(text)
        finally:
            if self.api_base:
                litellm.api_base = original_base

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        original_base = getattr(litellm, "api_base", None)
        try:
            if self.api_base:
                litellm.api_base = None
            return super().embed_documents(texts)
        finally:
            if self.api_base:
                litellm.api_base = original_base


class VectorStoreManager:
    """
    Manager for the Chroma vector store.
    """
    
    def __init__(
        self, 
        persist_directory: Optional[str] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        embedding_function: Optional[Embeddings] = None,
        settings: Optional[Settings] = None,
    ):
        """
        Initialize the VectorStoreManager.
        
        Args:
            persist_directory: Directory to persist the vector store.
            collection_name: Name of the collection in Chroma.
            embedding_model: Name of the embedding model to use (via LiteLLM).
            api_key: API key for the embedding model (optional, can be env var).
            embedding_function: Optional custom embedding function. If provided, overrides embedding_model.
        """
        knowledge = settings.knowledge if settings else None

        resolved_persist_directory = (
            persist_directory
            or (knowledge.vector_store.persist_directory if knowledge else None)
            or "./chroma_db"
        )
        resolved_collection_name = (
            collection_name
            or (knowledge.vector_store.collection_name if knowledge else None)
            or "knowledge_base"
        )

        self.persist_directory = resolved_persist_directory
        self.collection_name = resolved_collection_name
        
        # Initialize embeddings
        if embedding_function:
            self.embeddings = embedding_function
        else:
            model_name = (
                embedding_model
                or (knowledge.embeddings.model if knowledge else None)
                or os.getenv("LITELLM_EMBEDDING_MODEL")
                or "ollama/nomic-embed-text:v1.5"
            )
            e_api_key = (
                api_key
                or (knowledge.embeddings.api_key if knowledge else None)
                or os.getenv("LITELLM_EMBEDDING_API_KEY", "")
            )
            e_api_base = (
                api_base
                or (knowledge.embeddings.api_base if knowledge else None)
                or os.getenv("LITELLM_EMBEDDING_API_BASE", "")
            )
            
            self.embeddings = SafeLiteLLMEmbeddings(
                model=model_name,
                api_base=e_api_base,
                api_key=e_api_key,
            )
        
        # Initialize Chroma
        self.vector_store = Chroma(
            collection_name=resolved_collection_name,
            embedding_function=self.embeddings,
            persist_directory=resolved_persist_directory
        )

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents to add.
            
        Returns:
            List of IDs of the added documents.
        """
        if not documents:
            return []
        return self.vector_store.add_documents(documents)
        
    def similarity_search(self, query: str, k: int = 4) -> List[Document]:
        """
        Search for documents similar to the query.
        
        Args:
            query: The query string.
            k: The number of documents to return.
            
        Returns:
            List of matching documents.
        """
        return self.vector_store.similarity_search(query, k=k)

    def as_retriever(self, search_type: str = "similarity", search_kwargs: Optional[dict] = None):
        """
        Return the vector store as a retriever.
        
        Args:
            search_type: The search type ("similarity", "mmr", etc.).
            search_kwargs: Arguments to pass to the retriever (e.g. k, score_threshold).
            
        Returns:
            A retriever object.
        """
        # Default to k=4 if not specified
        kwargs = search_kwargs or {"k": 4}
        
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=kwargs
        )
