from typing import List, Optional, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from aiops.knowledge.vector_store import VectorStoreManager

class KnowledgeRetriever:
    """
    Retriever for the knowledge base.
    Wraps the vector store's retriever to provide a simplified interface.
    """
    
    def __init__(
        self,
        vector_store_manager: VectorStoreManager,
        search_type: str = "similarity",
        search_kwargs: Optional[dict] = None
    ):
        """
        Initialize the KnowledgeRetriever.
        
        Args:
            vector_store_manager: The VectorStoreManager instance.
            search_type: The search type ("similarity", "mmr", etc.).
            search_kwargs: Additional arguments for the search (e.g. k, score_threshold).
        """
        self.vector_store_manager = vector_store_manager
        
        # Use a more generous k by default for better recall
        default_kwargs = {"k": 6}
        if search_kwargs:
            default_kwargs.update(search_kwargs)
            
        self.retriever = vector_store_manager.as_retriever(
            search_type=search_type,
            search_kwargs=default_kwargs
        )

    def invoke(self, query: str) -> List[Document]:
        """
        Get relevant documents for a query.
        
        Args:
            query: The query string.
            
        Returns:
            List of relevant documents.
        """
        return self.retriever.invoke(query)

    def get_relevant_documents(self, query: str) -> List[Document]:
        """
        Get relevant documents for a query (alias for invoke).
        
        Args:
            query: The query string.
            
        Returns:
            List of relevant documents.
        """
        return self.invoke(query)
