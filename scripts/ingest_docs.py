import os
import sys
import glob
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiops.knowledge.processor import DocumentProcessor
from aiops.knowledge.vector_store import VectorStoreManager

def main():
    # Load environment variables
    load_dotenv()
    
    # Configuration
    docs_dir = "docs"
    persist_directory = "./chroma_db"
    
    # Check if docs directory exists
    if not os.path.exists(docs_dir):
        print(f"Error: Docs directory '{docs_dir}' not found.")
        return

    print(f"--- Starting Bulk Ingestion Process ---")
    
    # 1. Collect all markdown files
    md_files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)
    if not md_files:
        print(f"No markdown files found in '{docs_dir}'.")
        return
        
    print(f"Found {len(md_files)} markdown files in '{docs_dir}'.")
    
    # 2. Process Documents
    processor = DocumentProcessor()
    all_docs = []
    
    for file_path in md_files:
        print(f"Processing {file_path}...")
        try:
            docs = processor.process_file(file_path)
            # Add metadata about source
            for doc in docs:
                doc.metadata["source"] = file_path
                doc.metadata["filename"] = os.path.basename(file_path)
            all_docs.extend(docs)
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            continue

    print(f"Successfully processed {len(all_docs)} total document chunks.")
    
    if not all_docs:
        print("No documents to ingest.")
        return

    # 3. Initialize Vector Store and Add Documents
    print("Initializing Vector Store...")
    try:
        # Try with default configuration (LiteLLM) first
        vector_store = VectorStoreManager(persist_directory=persist_directory)
        
        print(f"Adding {len(all_docs)} documents to Vector Store...")
        ids = vector_store.add_documents(all_docs)
        print(f"Successfully added {len(ids)} documents to vector store at '{persist_directory}'.")
        
    except Exception as e:
        print(f"Error using default embeddings: {e}")
        print("Attempting to use local HuggingFace embeddings as fallback...")
        
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            # Use a small, fast model
            hf_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            
            # Use a different directory/collection to avoid dimension mismatch
            fallback_persist_directory = "./chroma_db_local"
            
            vector_store = VectorStoreManager(
                persist_directory=fallback_persist_directory,
                collection_name="knowledge_base_local",
                embedding_function=hf_embeddings
            )
            
            print(f"Adding {len(all_docs)} documents to Local Vector Store...")
            ids = vector_store.add_documents(all_docs)
            print(f"Successfully added {len(ids)} documents to vector store at '{fallback_persist_directory}' using local embeddings.")
            
            # Create a marker file to indicate fallback was used
            with open(".use_local_embeddings", "w") as f:
                f.write("true")
                
        except ImportError:
            print("langchain_huggingface or sentence-transformers not installed. Cannot use fallback.")
        except Exception as e2:
            print(f"Fallback failed: {e2}")

    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    main()
