import os
import sys
from pathlib import Path
import shutil

# Add project root to path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, project_root)

from langchain_core.documents import Document
from langchain_core.embeddings import FakeEmbeddings
from langchain_community.chat_models import FakeListChatModel
from langchain.tools import tool as lc_tool

try:
    from aiops.agents.customer_service import CustomerServiceAgent
    from knowledge.vector_store import VectorStoreManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def main():
    print("Starting Customer Service Agent Test (Mock Mode)...")
    
    # Initialize Vector Store with Fake Embeddings
    vs_dir = os.path.join(project_root, "chroma_db_test_cs")
    if os.path.exists(vs_dir):
        shutil.rmtree(vs_dir)
        
    embeddings = FakeEmbeddings(size=10)
    vs_manager = VectorStoreManager(
        collection_name="customer_service_test",
        persist_directory=vs_dir,
        embedding_function=embeddings
    )
    
    # Add mock documents
    docs = [
        Document(page_content="The return policy allows returns within 30 days of purchase for a full refund. Items must be in original condition.", metadata={"source": "policy"}),
        Document(page_content="Customer support is available 24/7 via email at support@example.com and phone at 1-800-123-4567.", metadata={"source": "support"}),
    ]
    vs_manager.add_documents(docs)
    print("Vector store initialized with mock data.")

    # Initialize Agent
    agent = CustomerServiceAgent(vs_manager)
    
    # Test Tool Logic Directly
    print("\n--- Testing Tool Logic ---")
    tools = agent.get_tools()
    query_tool = tools[0] # The closure function
    
    query1 = "What is the return policy?"
    print(f"Query: {query1}")
    result1 = query_tool(query1)
    print(f"Tool Result (first 50 chars): {result1[:50]}...")
    
    # Verify docs captured
    if len(agent.last_retrieved_docs) > 0:
        print(f"PASS: Tool captured {len(agent.last_retrieved_docs)} documents.")
    else:
        print("FAIL: Tool did not capture documents.")

    # Test Validator Logic
    print("\n--- Testing Validator Logic ---")
    # Case 1: Answer matches context
    answer1 = "You can return items within 30 days."
    valid1 = agent.validate_last_response(query1, answer1)
    print(f"Validation 1 (Should Pass): {'Pass' if valid1 else 'Fail'}")

    # Case 2: Answer is 'I don't know'
    agent.last_retrieved_docs = [] # Simulate no docs found
    answer2 = "I don't know."
    valid2 = agent.validate_last_response("Unknown query", answer2)
    print(f"Validation 2 (Should Pass for 'I don't know'): {'Pass' if valid2 else 'Fail'}")
    
    # Case 3: Hallucination (no context but specific answer)
    agent.last_retrieved_docs = []
    answer3 = "You can return items within 365 days."
    valid3 = agent.validate_last_response("Unknown query", answer3)
    # Note: Without LLM validator, my simple keyword check (which currently returns True always or based on logic) might be weak.
    # Let's check validator implementation.
    # It returns True if no context? No, if no context and not "I don't know", it returns False.
    print(f"Validation 3 (Should Fail): {'Fail' if not valid3 else 'Pass (Warning: Validator might be too lenient without LLM)'}")

    # Test Build (just to ensure no crash)
    print("\n--- Testing Agent Build ---")
    llm = FakeListChatModel(responses=["I don't know"])
    try:
        agent.build(llm)
        print("PASS: Agent build successful.")
    except Exception as e:
        print(f"FAIL: Agent build failed: {e}")

    # Cleanup
    if os.path.exists(vs_dir):
        shutil.rmtree(vs_dir)
        print("Cleanup done.")

if __name__ == "__main__":
    main()
