import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("TTS_API_KEY")
voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

print(f"[TTS CHECK] ElevenLabs Voice ID: {voice_id}")
if not api_key:
    print("[TTS CHECK][ERROR] ELEVENLABS_API_KEY / TTS_API_KEY is not configured.")
    exit(1)

url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
headers = {
    "xi-api-key": api_key,
    "Content-Type": "application/json",
    "Accept": "audio/mpeg",
}
data = {
    "text": "Hello, this is a test audio generation from ElevenLabs.",
    "model_id": "eleven_flash_v2_5",
}

try:
    response = requests.post(url, json=data, headers=headers)
    print(f"[TTS CHECK] HTTP Status: {response.status_code}")
    if response.status_code == 200:
        with open("tts_test.mp3", "wb") as f:
            f.write(response.content)
        print("[TTS CHECK] Success! Saved tts_test.mp3")
    else:
        print(f"[TTS CHECK] Error Body: {response.text}")
except Exception as e:
    print(f"[TTS CHECK] Exception during request: {e}")
