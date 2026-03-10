import os
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge.processor import DocumentProcessor
from knowledge.vector_store import VectorStoreManager

def main():
    # Load environment variables
    load_dotenv()
    
    # Configuration
    data_file = "data/sample_knowledge.md"
    persist_directory = "./chroma_db"
    
    # Check if data file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file '{data_file}' not found.")
        return

    print(f"--- Starting Ingestion Process ---")
    
    # 1. Process Document
    print(f"Processing {data_file}...")
    processor = DocumentProcessor()
    try:
        docs = processor.process_file(data_file)
        print(f"Successfully loaded and split into {len(docs)} chunks.")
    except Exception as e:
        print(f"Error processing file: {e}")
        return

    # 2. Initialize Vector Store
    print("Initializing Vector Store...")
    try:
        vector_store = VectorStoreManager(persist_directory=persist_directory)
        
        # 3. Add Documents
        print("Adding documents to Vector Store...")
        ids = vector_store.add_documents(docs)
        print(f"Successfully added {len(ids)} documents to vector store at '{persist_directory}'.")
        
    except Exception as e:
        print(f"Error using default embeddings: {e}")
        print("Attempting to use local HuggingFace embeddings as fallback...")
        
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            # Use a small, fast model
            hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            
            # Use a different directory/collection to avoid dimension mismatch
            fallback_persist_directory = "./chroma_db_local"
            
            vector_store = VectorStoreManager(
                persist_directory=fallback_persist_directory,
                collection_name="knowledge_base_local",
                # embedding_function=hf_embeddings
            )
            
            ids = vector_store.add_documents(docs)
            print(f"Successfully added {len(ids)} documents to vector store at '{fallback_persist_directory}' using local embeddings.")
            
            # Create a marker file to indicate fallback was used
            with open(".use_local_embeddings", "w") as f:
                f.write("true")
                
        except ImportError:
            print("langchain_community or sentence-transformers not installed. Cannot use fallback.")
        except Exception as e2:
            print(f"Fallback failed: {e2}")

    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    main()
