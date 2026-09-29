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
    model = cfg.LLM_MODEL if cfg.LLM_MODEL != "openai/gpt-oss-20b" else "llama-3.3-70b-versatile"

    logger.info(f"Initializing LLM service with provider: '{provider}', model: '{model}'")

    if provider in ("google", "gemini"):
        gemini_key = cfg.GEMINI_API_KEY or (cfg.LLM_API_KEY if cfg.LLM_PROVIDER in ("google", "gemini") else "")
        if gemini_key:
            try:
                from pipecat.services.google.llm import GoogleLLMService
                gemini_model = model if model and "llama" not in model else "gemini-2.0-flash"
                params = {}
                if hasattr(GoogleLLMService, "Settings"):
                    params["settings"] = GoogleLLMService.Settings(model=gemini_model)
                else:
                    params["model"] = gemini_model
                return GoogleLLMService(api_key=gemini_key, **params)
            except Exception as e:
                logger.warning(f"GoogleLLMService failed to initialize ({e}). Falling back to Groq LLM...")
        else:
            logger.warning("Gemini API key is not set. Falling back to Groq LLM...")

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

