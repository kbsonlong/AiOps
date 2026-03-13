import os
import sys
from dotenv import load_dotenv

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiops.knowledge.vector_store import VectorStoreManager
from aiops.knowledge.retriever import KnowledgeRetriever

def main():
    load_dotenv()
    
    print("--- Verifying Retrieval ---")
    
    # Check for local embeddings marker
    use_local = os.path.exists(".use_local_embeddings")
    
    # Initialize components
    try:
        if use_local:
            print("Using local embeddings (fallback mode)...")
            from langchain_huggingface import HuggingFaceEmbeddings
            # Suppress warnings if possible, or just let them show
            hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            
            vector_store = VectorStoreManager(
                persist_directory="./chroma_db_local",
                collection_name="knowledge_base_local",
                embedding_function=hf_embeddings
            )
        else:
            # Ensure persist_directory matches ingestion
            vector_store = VectorStoreManager(persist_directory="./chroma_db")
            
        retriever = KnowledgeRetriever(vector_store)
    except Exception as e:
        print(f"Error initializing retriever: {e}")
        return
    
    # Test queries
    queries = [
        "What is the AiOps system?",
        "How do I authenticate?",
        "介绍一下AIOPS?"
    ]
    
    for q in queries:
        print(f"\nQuery: {q}")
        try:
            docs = retriever.invoke(q)
            print(f"Found {len(docs)} documents.")
            if docs:
                for i, doc in enumerate(docs[:2]):
                    print(f"Result {i+1}: {doc.page_content[:150]}...")
            else:
                print("No documents found.")
        except Exception as e:
            print(f"Error retrieving documents: {e}")

if __name__ == "__main__":
    main()
