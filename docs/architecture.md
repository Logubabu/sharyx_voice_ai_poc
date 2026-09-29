# Architecture Documentation — Voice AI WebCall POC

## 1. High-Level Architecture

```text
React Browser Interface
       │
       │ WebRTC / REST
       ▼
Pipecat WebRTC Transport (Python FastAPI)
       │
       ▼
VAD / Turn Detection (Silero VAD)
       │
       ▼
STT Service Adapter (Sarvam AI / Groq / OpenAI / Deepgram)
       │
       ▼
LLM Service Adapter (Google Gemini / Groq / OpenAI)
       │
       ▼
TTS Service Adapter (ElevenLabs / Groq / OpenAI / Cartesia)
       │
       ▼
Pipecat WebRTC Transport
       │
       │ WebRTC Audio Output
       ▼
Browser Speakers
```

## 2. Component Design

### Frontend (React + Vite + TypeScript)
- **CallControls (`CallControls.tsx`)**: Manages call initiation (Start Call) and session termination (End Call).
- **CallStatus (`CallStatus.tsx`)**: Displays active state machine states (`Idle`, `Connecting...`, `Connected`, `Listening...`, `AI Speaking...`, `Ending...`, `Disconnected`, `Error`) and microphone status.
- **Transcript (`Transcript.tsx`)**: Renders real-time conversation messages.
- **Voice Service (`voice.ts`)**: Handles media permissions, API backend communication, and WebRTC session management.

### Backend (Python + Pipecat + FastAPI)
- **Main (`app/main.py`)**: FastAPI web server exposing `/api/start`, `/api/stop`, `/api/status`, and `/health`.
- **Config (`app/config.py`)**: Manages environment variables securely using Pydantic and `python-dotenv`.
- **Transport (`app/transport.py`)**: WebRTC transport adapter using Pipecat `DailyTransport` or `SmallWebRTCTransport`.
- **Pipeline (`app/pipeline.py`)**: Assembles real-time streaming pipeline (`STT -> LLM -> TTS`) with interruption and turn management.
- **Service Adapters (`app/services/`)**: Decoupled provider adapters for STT, LLM, and TTS services.

## 3. Call Lifecycle

1. User opens web application and clicks **Start Call**.
2. Browser requests microphone access via `getUserMedia()`.
3. React app sends POST to `/api/start`.
4. Backend creates room credentials and spawns Pipecat pipeline in an asynchronous worker.
5. React app establishes WebRTC connection with Pipecat backend.
6. User speaks; microphone audio streams to Pipecat STT.
7. Recognized text flows to LLM; LLM stream flows to TTS.
8. AI audio streams back over WebRTC and plays in browser speakers.
9. Click **End Call** closes WebRTC peer connection, releases microphone, and stops backend Pipecat session worker.
10. Application returns to `Idle` state, ready for another call without page refresh.
