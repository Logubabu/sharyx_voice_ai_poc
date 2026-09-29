from typing import Any
from app.config import Config
from app.utils.logging import logger


def create_tts_service(cfg: Config) -> Any:
    """Factory function to create TTS service adapter based on config.
    
    Supports:
    - openai: OpenAITTSService
    - elevenlabs: ElevenLabsTTSService
    - cartesia: CartesiaTTSService
    """
    provider = cfg.TTS_PROVIDER.lower()
    api_key = cfg.TTS_API_KEY or cfg.LLM_API_KEY or cfg.GROQ_API_KEY

    logger.info(f"Initializing TTS service with provider: '{provider}'")

    if provider == "groq":
        try:
            from pipecat.services.groq.tts import GroqTTSService
            return GroqTTSService(api_key=api_key)
        except Exception as e:
            logger.warning(f"GroqTTSService not available ({e}). Trying OpenAITTSService...")

    if provider == "openai":
        try:
            from pipecat.services.openai.tts import OpenAITTSService
            return OpenAITTSService(api_key=api_key or "mock-key", voice="alloy")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAITTSService: {e}")

    if provider == "elevenlabs":
        try:
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
            return ElevenLabsTTSService(api_key=api_key)
        except Exception as e:
            logger.warning(f"Could not initialize ElevenLabsTTSService: {e}")

    if provider == "cartesia":
        try:
            from pipecat.services.cartesia.tts import CartesiaTTSService
            return CartesiaTTSService(api_key=api_key, voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22")
        except Exception as e:
            logger.warning(f"Could not initialize CartesiaTTSService: {e}")

    try:
        from pipecat.services.openai.tts import OpenAITTSService
        return OpenAITTSService(api_key=api_key or "mock-key", voice="alloy")
    except Exception as e:
        logger.error(f"Failed to create TTS service adapter: {e}")
        raise RuntimeError(f"Unsupported or failed TTS provider: '{provider}'") from e


