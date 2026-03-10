
import os
from aiops.agents.customer_service import CustomerServiceAgent
from knowledge.vector_store import VectorStoreManager
from langchain_litellm import ChatLiteLLM

def main():
    print("Initializing VectorStoreManager...")
    vs = VectorStoreManager()
    print("VectorStoreManager initialized.")
    
    print("Testing retrieval directly...")
    docs = vs.similarity_search("What is the AiOps system?")
    print(f"Retrieved {len(docs)} docs.")
    for i, doc in enumerate(docs):
        print(f"Doc {i}: {doc.page_content[:100]}...")

    print("\nInitializing CustomerServiceAgent...")
    llm = ChatLiteLLM(model=os.getenv("LLM_MODEL"), api_key="ollama", api_base="http://localhost:11434")
    agent = CustomerServiceAgent(vs).build(llm)
    
    print("Invoking agent...")
    result = agent.invoke({"messages": [{"role": "user", "content": "What is the AiOps system?"}]})
    print("Agent Result:", result["messages"][-1].content)

if __name__ == "__main__":
    main()
