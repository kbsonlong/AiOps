
import os
from litellm import completion
from langchain_litellm import ChatLiteLLM
from dotenv import load_dotenv

load_dotenv()

def test_deepseek():
    api_key = os.getenv("LITELLM_API_KEY")
    api_base = os.getenv("LITELLM_API_BASE")
    model = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")

    print(f"Testing DeepSeek with:")
    print(f"Model: {model}")
    print(f"API Base: {api_base}")
    print(f"API Key: {api_key[:5]}...{api_key[-4:] if api_key else 'None'}")

    print("\n--- Test 1: litellm.completion with api_base ---")
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": "Hello from completion."}],
            api_key=api_key,
            api_base=api_base
        )
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Test 2: ChatLiteLLM with api_base ---")
    try:
        llm = ChatLiteLLM(model=model, api_key=api_key, api_base=api_base)
        response = llm.invoke("Hello from ChatLiteLLM.")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Test 3: ChatOpenAI (DeepSeek) ---")
    try:
        from langchain_openai import ChatOpenAI
        llm_openai = ChatOpenAI(
            model="deepseek-chat", # OpenAI client usually needs clean model name
            api_key=api_key,
            base_url=api_base
        )
        response = llm_openai.invoke("Hello from ChatOpenAI.")
        print("Success!")
        print(response.content)
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Test 4: ChatLiteLLM as OpenAI ---")
    try:
        # Treat DeepSeek as a generic OpenAI provider
        llm = ChatLiteLLM(
            model="deepseek-chat", 
            api_key=api_key, 
            api_base=api_base,
            custom_llm_provider="openai"
        )
        response = llm.invoke("Hello from ChatLiteLLM as OpenAI.")
        print("Success!")
        print(response.content)
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Test 5: ChatLiteLLM with openai/ prefix ---")
    try:
        # LiteLLM parses "openai/model_name" as provider=openai, model=model_name
        llm = ChatLiteLLM(
            model="openai/deepseek-chat", 
            api_key=api_key, 
            api_base=api_base
        )
        response = llm.invoke("Hello from ChatLiteLLM via openai/ prefix.")
        print("Success!")
        print(response.content)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_deepseek()
