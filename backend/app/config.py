import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


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
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "elevenlabs").lower()
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "") or os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    ELEVENLABS_MODEL: str = os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Audio Processor & Telephony Integration Config
    AUDIO_PROCESSOR: str = os.getenv("AUDIO_PROCESSOR", "RNNoise")
    FREESWITCH_ENABLED: bool = os.getenv("FREESWITCH_ENABLED", "true").lower() in ("true", "1", "yes")
    FREESWITCH_HOST: str = os.getenv("FREESWITCH_HOST", "127.0.0.1:8021")
    TOOL_CALLING_ENABLED: bool = os.getenv("TOOL_CALLING_ENABLED", "true").lower() in ("true", "1", "yes")

    # Web Search & Web Fetch Configuration
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8080")
    WEB_SEARCH_ENABLED: bool = os.getenv("WEB_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
    WEB_SEARCH_MAX_RESULTS: int = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "5"))
    WEB_SEARCH_TIMEOUT: float = float(os.getenv("WEB_SEARCH_TIMEOUT", "8"))
    WEB_FETCH_TIMEOUT: float = float(os.getenv("WEB_FETCH_TIMEOUT", "10"))
    WEB_FETCH_MAX_BYTES: int = int(os.getenv("WEB_FETCH_MAX_BYTES", "2000000"))


    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000").split(",")
        if origin.strip() and origin.strip() != "*"
    ]

    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        (
            "You are a helpful, conversational Voice AI assistant with real-time web search capabilities.\n\n"
            "Tool Usage Rules:\n"
            "1. Call `web_search(query)` immediately whenever the user asks about live internet data, recent news, current events, latest AI models, real-time prices, or recent updates.\n"
            "2. Call `web_fetch(url)` if search snippets are insufficient and you need to read full webpage content.\n"
            "3. Do NOT call web_search for static general knowledge or basic concepts (e.g., 'What is Python?'). Answer static questions directly.\n"
            "4. Use internal tools (`check_order_status`, `get_customer_info`, `book_appointment`, `transfer_call`) only when explicitly asked by the user.\n\n"
            "Voice Response Style:\n"
            "- Speak naturally in 1 to 2 short, conversational sentences.\n"
            "- Never mention tool names, raw JSON, or tool errors unless a tool explicitly returned a failure.\n"
            "- Answer directly using the tool result."
        ),
    )



config = Config()

