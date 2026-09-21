import os
from autonomy.llm.openai_llm import OpenAILLM

def get_llm() -> OpenAILLM:
    provider = os.getenv("LLM_PROVIDER")

    if not provider:
        raise ValueError("LLM_Provider must be set...")

    # testing agent
    if provider == "ollama":
        return OpenAILLM(
            model_name=os.getenv("LLM_MODEL", "qwen2.5:7b-instruct-q4_K_M"),
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"), # Ollama's default host port
            temperature=float(os.getenv("LLM_TEMPERATURE", "0"))
        )

    # fallback/benchmark agent
    elif provider == "openai":
        return OpenAILLM(
            model_name=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0"))
        )
        
    # production agent
    elif provider == "vllm":
        base_url = os.getenv("LLM_BASE_URL")
        if not base_url:
            raise ValueError("LLM_BASE_URL must be set when LLM_PROVIDER=vllm")

        model_name = os.getenv("LLM_MODEL")
        if not model_name:
            raise ValueError("LLM_MODEL must be set when LLM_PROVIDER=vllm")
        
        return OpenAILLM(
            model_name=model_name,
            base_url=base_url,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0"))
        )

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")