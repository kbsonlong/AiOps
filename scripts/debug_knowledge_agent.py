
import os
from dotenv import load_dotenv
from aiops.agents.knowledge_agent import KnowledgeAgent
from aiops.knowledge.vector_store import VectorStoreManager
from langchain_litellm import ChatLiteLLM

def main():
    load_dotenv()
    print("Initializing VectorStoreManager...")
    vs = VectorStoreManager()
    print("VectorStoreManager initialized.")
    
    print("Testing retrieval directly...")
    docs = vs.similarity_search("What is the AiOps system?")
    print(f"Retrieved {len(docs)} docs.")
    for i, doc in enumerate(docs):
        print(f"Doc {i}: {doc.page_content[:100]}...")

    print("\nInitializing KnowledgeAgent...")
    llm_model = os.getenv("LLM_MODEL")
    api_key = os.getenv("LITELLM_API_KEY")
    api_base = os.getenv("LITELLM_API_BASE")
    # api_base is handled by LiteLLM via LITELLM_API_BASE env var for openai/* models
    # But explicitly passing it is safer if we read it from env
    llm = ChatLiteLLM(model=llm_model, api_key=api_key, api_base=api_base)
    
    agent = KnowledgeAgent(vs).build(llm)
    
    print("Invoking agent...")
    result = agent.invoke({"messages": [{"role": "user", "content": "What is the AiOps system?"}]})
    print("Agent Result:", result["messages"][-1].content)

if __name__ == "__main__":
    main()
