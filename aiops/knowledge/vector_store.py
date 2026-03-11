import os
from typing import List, Optional, Any
from langchain_chroma import Chroma
from langchain_litellm import LiteLLMEmbeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

class VectorStoreManager:
    """
    Manager for the Chroma vector store.
    """
    
    def __init__(
        self, 
        persist_directory: str = "./chroma_db",
        collection_name: str = "knowledge_base",
        embedding_model: str = "ollama/nomic-embed-text:v1.5", 
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        embedding_function: Optional[Embeddings] = None
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
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Initialize embeddings
        if embedding_function:
            self.embeddings = embedding_function
        else:
            # Ensure API key is available if needed
            if api_base:
                os.environ["LITELLM_EMBEDDING_API_BASE"] = api_base
            if api_key:
                os.environ["LITELLM_EMBEDDING_API_KEY"] = api_key
            
            os.environ["LITELLM_EMBEDDING_MODEL"] = embedding_model
            
            self.embeddings = LiteLLMEmbeddings(
                model=embedding_model,
                api_base=api_base,
                api_key=api_key,
            )
        
        # Initialize Chroma
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory
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

    def as_retriever(self, **kwargs: Any):
        """
        Return the vector store as a retriever.
        
        Args:
            **kwargs: Arguments to pass to the retriever (e.g. search_kwargs).
            
        Returns:
            A retriever object.
        """
        return self.vector_store.as_retriever(**kwargs)
