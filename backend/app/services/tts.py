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
        el_key = cfg.ELEVENLABS_API_KEY or (cfg.TTS_API_KEY if cfg.TTS_PROVIDER == "elevenlabs" else "")
        if el_key:
            try:
                from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
                params = {}
                if hasattr(ElevenLabsTTSService, "Settings"):
                    params["settings"] = ElevenLabsTTSService.Settings(voice=cfg.ELEVENLABS_VOICE_ID)
                else:
                    params["voice_id"] = cfg.ELEVENLABS_VOICE_ID
                return ElevenLabsTTSService(api_key=el_key, **params)
            except Exception as e:
                logger.warning(f"Could not initialize ElevenLabsTTSService ({e}). Falling back to Groq TTS...")
        else:
            logger.warning("ElevenLabs API key is not set. Falling back to Groq TTS...")

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


