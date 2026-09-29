from typing import Any
from app.config import Config
from app.utils.logging import logger


def create_llm_service(cfg: Config) -> Any:
    """Factory function to create LLM service adapter based on config.
    
    Supports:
    - groq: GroqLLMService (or OpenAILLMService with Groq base URL)
    - openai: OpenAILLMService
    - custom adapters
    """
    provider = cfg.LLM_PROVIDER.lower()
    api_key = cfg.LLM_API_KEY or cfg.GROQ_API_KEY
    model = cfg.LLM_MODEL or "openai/gpt-oss-20b"

    logger.info(f"Initializing LLM service with provider: '{provider}', model: '{model}'")

    if provider == "groq":
        try:
            from pipecat.services.groq.llm import GroqLLMService
            return GroqLLMService(api_key=api_key or "mock-key", model=model)
        except Exception as e:
            logger.warning(f"GroqLLMService import/init failed: {e}. Trying OpenAILLMService with Groq endpoint...")
            try:
                from pipecat.services.openai.llm import OpenAILLMService
                return OpenAILLMService(
                    api_key=api_key or "mock-key",
                    base_url="https://api.groq.com/openai/v1",
                    model=model,
                )
            except Exception as ex:
                logger.error(f"Failed to initialize Groq via OpenAILLMService adapter: {ex}")
                raise RuntimeError(f"Failed to create Groq LLM service adapter: {ex}") from ex

    if provider == "openai":
        try:
            from pipecat.services.openai.llm import OpenAILLMService
            return OpenAILLMService(api_key=api_key or "mock-key", model=model if cfg.LLM_MODEL != "llama-3.3-70b-versatile" else "gpt-4o-mini")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAILLMService: {e}")

    try:
        from pipecat.services.openai.llm import OpenAILLMService
        return OpenAILLMService(api_key=api_key or "mock-key", model="gpt-4o-mini")
    except Exception as e:
        logger.error(f"Failed to create LLM service adapter: {e}")
        raise RuntimeError(f"Unsupported or failed LLM provider: '{provider}'") from e

