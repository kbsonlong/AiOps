import os
from typing import List, Optional
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class DocumentProcessor:
    """
    Processor for loading and splitting documents from various formats.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Initialize the DocumentProcessor.
        
        Args:
            chunk_size: The size of the chunks to split the documents into.
            chunk_overlap: The overlap between chunks.
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """
        Load a document from a file path.
        
        Args:
            file_path: The path to the file to load.
            
        Returns:
            A list of Document objects.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Always use TextLoader for better compatibility and simple text extraction
        try:
            loader = TextLoader(file_path, encoding='utf-8')
            return loader.load()
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
            return []

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks.
        
        Args:
            documents: The list of documents to split.
            
        Returns:
            A list of split Document objects.
        """
        return self.text_splitter.split_documents(documents)
    
    def process_file(self, file_path: str) -> List[Document]:
        """
        Load and split a document from a file path.
        
        Args:
            file_path: The path to the file to process.
            
        Returns:
            A list of processed (split) Document objects.
        """
        docs = self.load_document(file_path)
        return self.split_documents(docs)
