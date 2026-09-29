import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


class Config:
    """Application configuration from environment variables."""

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Provider configurations
    STT_PROVIDER: str = os.getenv("STT_PROVIDER", "groq").lower()
    STT_API_KEY: str = os.getenv("STT_API_KEY", "")

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").lower()
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "groq").lower()
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")

    # Daily / WebRTC configurations
    DAILY_API_KEY: str = os.getenv("DAILY_API_KEY", "")
    DAILY_ROOM_URL: str = os.getenv("DAILY_ROOM_URL", "")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,*").split(",")
        if origin.strip()
    ]

    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT",
        (
            "You are a helpful Voice AI assistant.\n\n"
            "Keep your responses concise and conversational because your responses will be spoken aloud.\n\n"
            "Do not produce unnecessary long explanations.\n\n"
            "If the user interrupts you, stop your current response and listen to the user's new request."
        ),
    )


config = Config()
