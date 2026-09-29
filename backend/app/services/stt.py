from typing import Any
from app.config import Config
from app.utils.logging import logger


def create_stt_service(cfg: Config) -> Any:
    """Factory function to create STT service adapter based on config.
    Strictly enforces STT_PROVIDER without silent fallbacks.
    """
    provider = cfg.STT_PROVIDER.lower()
    logger.info(f"[PIPELINE] Creating STT (Provider: '{provider}')")

    if provider == "sarvam":
        sarvam_key = cfg.SARVAM_API_KEY or cfg.STT_API_KEY
        if not sarvam_key:
            logger.error("[STT][FATAL] Sarvam API key is not configured (SARVAM_API_KEY or STT_API_KEY missing).")
            raise RuntimeError("Sarvam STT initialization failed: SARVAM_API_KEY is not configured.")
        try:
            from pipecat.services.sarvam.stt import SarvamSTTService
            params = {}
            if hasattr(SarvamSTTService, "Settings"):
                params["settings"] = SarvamSTTService.Settings(model=cfg.SARVAM_MODEL)
            else:
                params["model"] = cfg.SARVAM_MODEL
            service = SarvamSTTService(api_key=sarvam_key, **params)
            logger.info(f"[STT] Provider: sarvam | Model: {cfg.SARVAM_MODEL} | Initialized")
            return service
        except Exception as e:
            logger.exception(f"[STT][FATAL] Sarvam STT initialization failed: {e}")
            raise RuntimeError(f"Sarvam STT initialization failed: {e}") from e

    if provider == "groq":
        groq_key = cfg.STT_API_KEY or cfg.GROQ_API_KEY
        if not groq_key:
            logger.error("[STT][FATAL] Groq STT API key is not configured.")
            raise RuntimeError("Groq STT initialization failed: API key missing.")
        try:
            from pipecat.services.groq.stt import GroqSTTService
            return GroqSTTService(api_key=groq_key)
        except Exception as e:
            logger.exception(f"[STT][FATAL] Groq STT initialization failed: {e}")
            raise RuntimeError(f"Groq STT initialization failed: {e}") from e

    logger.error(f"[STT][FATAL] Unsupported STT provider: '{provider}'")
    raise RuntimeError(f"Unsupported STT provider: '{provider}'")
