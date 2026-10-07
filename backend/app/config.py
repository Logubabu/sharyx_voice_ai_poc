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
            "You are a fast, conversational Voice AI assistant.\n\n"
            "You have access to a Tool Registry with function calling capabilities:\n"
            "- check_order_status(order_id): Look up customer order status (e.g., ORD-101, ORD-102)\n"
            "- get_customer_info(phone): Look up customer account profile\n"
            "- transfer_call(department, reason): Escalate or transfer call to human agent / FreeSWITCH queue\n"
            "- book_appointment(date, time_slot, service_type): Schedule appointments\n\n"
            "When asked about an order or booking, call the appropriate function tool immediately.\n"
            "Keep your spoken responses extremely concise in 1 to 2 short sentences max.\n"
            "Reply in plain spoken sentences only. No markdown formatting, bullet points, emojis or special characters."
        ),
    )


config = Config()
