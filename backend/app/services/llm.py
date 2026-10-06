from typing import Any
from app.config import Config
from app.utils.logging import logger


def create_llm_service(cfg: Config) -> Any:
    """Factory function to create LLM service adapter based on config.
    Strictly enforces LLM_PROVIDER without silent fallbacks.
    """
    provider = cfg.LLM_PROVIDER.lower()
    model = cfg.LLM_MODEL
    logger.info(f"[PIPELINE] Creating LLM (Provider: '{provider}', Model: '{model}')")

    if provider in ("google", "gemini"):
        gemini_key = cfg.GEMINI_API_KEY or cfg.LLM_API_KEY
        if not gemini_key:
            logger.error("[LLM][FATAL] Gemini API key is not configured (GEMINI_API_KEY or LLM_API_KEY missing).")
            raise RuntimeError("Google Gemini LLM initialization failed: GEMINI_API_KEY is not configured.")
        try:
            from pipecat.services.google.llm import GoogleLLMService
            from app.services.tools import tool_registry

            gemini_model = model if model and "llama" not in model else "gemini-3.5-flash-lite"
            params = {}
            if hasattr(GoogleLLMService, "Settings"):
                params["settings"] = GoogleLLMService.Settings(model=gemini_model)
            else:
                params["model"] = gemini_model
            service = GoogleLLMService(api_key=gemini_key, **params)
            
            # Register Tool Registry function definitions & handlers on Gemini service
            tool_registry.register_tools_on_llm(service)
            logger.info(f"[LLM] Provider: google | Model: {gemini_model} | Tools: {len(tool_registry.get_tool_definitions())} Registered")
            return service
        except Exception as e:
            logger.exception(f"[LLM][FATAL] Google LLM initialization failed: {e}")
            raise RuntimeError(f"Google LLM initialization failed: {e}") from e

    if provider == "groq":
        groq_key = cfg.LLM_API_KEY or cfg.GROQ_API_KEY
        if not groq_key:
            logger.error("[LLM][FATAL] Groq LLM API key is not configured.")
            raise RuntimeError("Groq LLM initialization failed: API key missing.")
        try:
            from pipecat.services.groq.llm import GroqLLMService
            return GroqLLMService(api_key=groq_key, model=model)
        except Exception as e:
            logger.exception(f"[LLM][FATAL] Groq LLM initialization failed: {e}")
            raise RuntimeError(f"Groq LLM initialization failed: {e}") from e

    logger.error(f"[LLM][FATAL] Unsupported LLM provider: '{provider}'")
    raise RuntimeError(f"Unsupported LLM provider: '{provider}'")
