from typing import Any
from app.config import Config
from app.utils.logging import logger


def create_tts_service(cfg: Config) -> Any:
    """Factory function to create TTS service adapter based on config.
    Strictly enforces TTS_PROVIDER without silent fallbacks.
    """
    provider = cfg.TTS_PROVIDER.lower()
    logger.info(f"[PIPELINE] Creating TTS (Provider: '{provider}')")

    if provider == "elevenlabs":
        el_key = cfg.ELEVENLABS_API_KEY or cfg.TTS_API_KEY
        if not el_key:
            logger.error("[TTS][FATAL] ElevenLabs API key is not configured (ELEVENLABS_API_KEY or TTS_API_KEY missing).")
            raise RuntimeError("ElevenLabs TTS initialization failed: ELEVENLABS_API_KEY is not configured.")
        try:
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
            params = {}
            if hasattr(ElevenLabsTTSService, "Settings"):
                params["settings"] = ElevenLabsTTSService.Settings(voice=cfg.ELEVENLABS_VOICE_ID)
            else:
                params["voice_id"] = cfg.ELEVENLABS_VOICE_ID
            service = ElevenLabsTTSService(api_key=el_key, **params)
            logger.info(f"[TTS] Provider: elevenlabs | Voice ID: {cfg.ELEVENLABS_VOICE_ID} | Initialized")
            return service
        except Exception as e:
            logger.exception(f"[TTS][FATAL] ElevenLabs TTS initialization failed: {e}")
            raise RuntimeError(f"ElevenLabs TTS initialization failed: {e}") from e

    if provider == "groq":
        groq_key = cfg.TTS_API_KEY or cfg.GROQ_API_KEY
        if not groq_key:
            logger.error("[TTS][FATAL] Groq TTS API key is not configured.")
            raise RuntimeError("Groq TTS initialization failed: API key missing.")
        try:
            from pipecat.services.groq.tts import GroqTTSService
            return GroqTTSService(api_key=groq_key)
        except Exception as e:
            logger.exception(f"[TTS][FATAL] Groq TTS initialization failed: {e}")
            raise RuntimeError(f"Groq TTS initialization failed: {e}") from e

    logger.error(f"[TTS][FATAL] Unsupported TTS provider: '{provider}'")
    raise RuntimeError(f"Unsupported TTS provider: '{provider}'")
