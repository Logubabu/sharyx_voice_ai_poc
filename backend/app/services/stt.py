from typing import Any
from app.config import Config
from app.utils.logging import logger


def create_stt_service(cfg: Config) -> Any:
    """Factory function to create STT service adapter based on config.
    
    Supports:
    - groq: GroqSTTService
    - openai: OpenAISTTService
    - deepgram: DeepgramSTTService
    """
    provider = cfg.STT_PROVIDER.lower()
    api_key = cfg.STT_API_KEY or cfg.LLM_API_KEY or cfg.GROQ_API_KEY

    logger.info(f"Initializing STT service with provider: '{provider}'")

    if provider == "groq":
        try:
            from pipecat.services.groq.stt import GroqSTTService
            return GroqSTTService(api_key=api_key)
        except Exception as e:
            logger.warning(f"GroqSTTService not available ({e}). Trying OpenAISTTService with Groq endpoint...")
            try:
                from pipecat.services.openai.stt import OpenAISTTService
                return OpenAISTTService(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            except Exception as ex:
                logger.warning(f"OpenAISTTService with Groq endpoint failed: {ex}")

    if provider == "openai":
        try:
            from pipecat.services.openai.stt import OpenAISTTService
            return OpenAISTTService(api_key=api_key)
        except Exception as e:
            logger.warning(f"Could not initialize OpenAISTTService: {e}. Falling back to default.")

    if provider == "deepgram":
        try:
            from pipecat.services.deepgram.stt import DeepgramSTTService
            return DeepgramSTTService(api_key=api_key)
        except Exception as e:
            logger.warning(f"Could not initialize DeepgramSTTService: {e}. Falling back to default.")

    # Fallback attempt
    try:
        from pipecat.services.openai.stt import OpenAISTTService
        return OpenAISTTService(api_key=api_key or "mock-key")
    except Exception as e:
        logger.error(f"Failed to create STT service adapter: {e}")
        raise RuntimeError(f"Unsupported or failed STT provider: '{provider}'") from e


