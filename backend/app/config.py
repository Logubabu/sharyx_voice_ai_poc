import os
from typing import List, Any
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


def _safe_int(val: Any, default: int) -> int:
    try:
        if val is None or str(val).strip() == "":
            return default
        return int(float(val))
    except Exception:
        return default


def _safe_float(val: Any, default: float) -> float:
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(val)
    except Exception:
        return default


class Config:
    """Application configuration from environment variables."""

    # Provider configurations
    STT_PROVIDER: str = os.getenv("STT_PROVIDER", "sarvam").lower()
    STT_API_KEY: str = os.getenv("STT_API_KEY", "") or os.getenv("SARVAM_API_KEY", "")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    SARVAM_MODEL: str = os.getenv("SARVAM_MODEL", "saaras:v3")
    SARVAM_TTS_MODEL: str = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
    SARVAM_TTS_VOICE: str = os.getenv("SARVAM_TTS_VOICE", "shubh")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google").lower()
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")

    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "elevenlabs").lower()
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "") or os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    VOICE_DEBUG_AUDIO: bool = os.getenv("VOICE_DEBUG_AUDIO", "true").lower() in ("true", "1", "yes")

    # Audio Processor & Telephony Integration Config
    AUDIO_PROCESSOR: str = os.getenv("AUDIO_PROCESSOR", "passthrough")
    FREESWITCH_ENABLED: bool = os.getenv("FREESWITCH_ENABLED", "true").lower() in ("true", "1", "yes")
    FREESWITCH_HOST: str = os.getenv("FREESWITCH_HOST", "127.0.0.1:8021")
    TOOL_CALLING_ENABLED: bool = os.getenv("TOOL_CALLING_ENABLED", "true").lower() in ("true", "1", "yes")
    WEBCALL_TOOL_CALLING_ENABLED: bool = os.getenv("WEBCALL_TOOL_CALLING_ENABLED", os.getenv("TOOL_CALLING_ENABLED", "true")).lower() in ("true", "1", "yes")
    WEBCALL_WEB_SEARCH_ENABLED: bool = os.getenv("WEBCALL_WEB_SEARCH_ENABLED", os.getenv("WEB_SEARCH_ENABLED", "true")).lower() in ("true", "1", "yes")
    MAX_TOOL_CALLS_PER_TURN: int = _safe_int(os.getenv("MAX_TOOL_CALLS_PER_TURN"), 3)
    MAX_WEB_SEARCHES_PER_SESSION: int = _safe_int(os.getenv("MAX_WEB_SEARCHES_PER_SESSION"), 20)

    # Web Search & Web Fetch Configuration
    SEARCH_PROVIDER: str = os.getenv("WEB_SEARCH_PROVIDER", os.getenv("SEARCH_PROVIDER", "duckduckgo")).lower()
    WEB_SEARCH_PROVIDER: str = os.getenv("WEB_SEARCH_PROVIDER", os.getenv("SEARCH_PROVIDER", "duckduckgo")).lower()
    WEB_SEARCH_API_KEY: str = os.getenv("WEB_SEARCH_API_KEY", os.getenv("SEARCH_API_KEY", ""))
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    BING_API_KEY: str = os.getenv("BING_API_KEY", "")
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8000")
    WEB_SEARCH_ENABLED: bool = os.getenv("WEB_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
    WEB_SEARCH_MAX_RESULTS: int = _safe_int(os.getenv("WEB_SEARCH_MAX_RESULTS"), 5)
    WEB_SEARCH_TIMEOUT: float = _safe_float(os.getenv("WEB_SEARCH_TIMEOUT"), 5.0)
    WEB_SEARCH_CACHE_TTL: float = _safe_float(os.getenv("WEB_SEARCH_CACHE_TTL"), 0.0)
    WEB_FETCH_TIMEOUT: float = _safe_float(os.getenv("WEB_FETCH_TIMEOUT"), 10.0)
    WEB_FETCH_MAX_BYTES: int = _safe_int(os.getenv("WEB_FETCH_MAX_BYTES"), 2000000)

    # Twilio REST API Configuration
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "") or os.getenv("TWILIO_FROM_NUMBER", "+17372508034")
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "")
    TWILIO_WEBHOOK_BASE_URL: str = os.getenv("TWILIO_WEBHOOK_BASE_URL", "") or os.getenv("PUBLIC_BASE_URL", "")
    TWILIO_VALIDATE_SIGNATURE: bool = os.getenv("TWILIO_VALIDATE_SIGNATURE", "false").lower() in ("true", "1", "yes")

    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000").split(",")
        if origin.strip() and origin.strip() != "*"
    ]

    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        (
            "You are a helpful, real-time Voice AI assistant with dynamic web search tool-calling capabilities.\n\n"
            "Tool Calling Rules:\n"
            "1. Dynamic Search Decision:\n"
            "   - CALL `web_search(query)` whenever the user asks for real-time, current, changing, or externally verifiable information.\n"
            "     Examples: current stock prices, crypto prices, weather today, latest sports scores, current events, recent news, today's headlines, recent AI/tech releases, product availability, or live market data.\n"
            "   - Do NOT call `web_search` for static general knowledge, code explanations, or basic concepts (e.g., 'What is Python?', 'What is FastAPI?', 'What is MongoDB?'). Answer static queries directly.\n\n"
            "2. Search Query Optimization:\n"
            "   - Convert the user's spoken request into a concise search query.\n"
            "   - Remove conversational filler ('hey tell me', 'can you find out') and correct obvious STT speech artifacts.\n"
            "   - Preserve critical entities, company names, locations, dates, and numerical constraints.\n"
            "   - Resolve pronouns using recent conversation context (e.g. 'Tesla stock price' -> 'How much did it change today?' -> query: 'Tesla stock price change today').\n\n"
            "3. Voice Response Format:\n"
            "   - Provide concise, natural conversational answers suitable for speech (1 to 3 short sentences).\n"
            "   - Never speak raw URLs, markdown tables, or tool execution details.\n"
            "   - Use natural attributions like 'According to recent market data...' or 'Recent news reports indicate...'.\n"
            "   - If search fails or yields no results, gracefully answer based on your internal knowledge."
        ),
    )


config = Config()
