import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import config
from app.pipeline import pipeline_manager
from app.utils.logging import logger

app = FastAPI(
    title="Voice AI WebCall POC",
    description="Real-time Voice AI WebCall POC Backend powered by Pipecat",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def warm_up_services():
    """Pre-warms service adapters and logs provider status."""
    logger.info("Pre-warming voice service pipeline adapters...")
    sarvam_configured = bool(config.SARVAM_API_KEY or config.STT_API_KEY)
    gemini_configured = bool(config.GEMINI_API_KEY or config.LLM_API_KEY)
    elevenlabs_configured = bool(config.ELEVENLABS_API_KEY or config.TTS_API_KEY)

    logger.info(f"[CONFIG] SARVAM_API_KEY: {'configured' if sarvam_configured else 'NOT CONFIGURED'}")
    logger.info(f"[CONFIG] GEMINI_API_KEY: {'configured' if gemini_configured else 'NOT CONFIGURED'}")
    logger.info(f"[CONFIG] ELEVENLABS_API_KEY: {'configured' if elevenlabs_configured else 'NOT CONFIGURED'}")

    try:
        from app.services.stt import create_stt_service
        from app.services.llm import create_llm_service
        from app.services.tts import create_tts_service
        create_stt_service(config)
        create_llm_service(config)
        create_tts_service(config)
        logger.info("[CONFIG] Voice pipeline pre-warming complete. Backend ready for requests.")
    except Exception as e:
        logger.warning(f"[CONFIG] Pre-warming notice: {e}")


from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequestHandler, SmallWebRTCRequest
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

webrtc_request_handler = SmallWebRTCRequestHandler()


class StartCallRequest(BaseModel):
    session_id: str | None = None


class StopCallRequest(BaseModel):
    session_id: str


class OfferRequest(BaseModel):
    sdp: str
    type: str = "offer"
    pc_id: str | None = None
    session_id: str | None = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/config/status")
async def get_config_status():
    """Reports configuration status of required providers without revealing secrets."""
    return {
        "sarvam": bool(config.SARVAM_API_KEY or config.STT_API_KEY),
        "gemini": bool(config.GEMINI_API_KEY or config.LLM_API_KEY),
        "elevenlabs": bool(config.ELEVENLABS_API_KEY or config.TTS_API_KEY),
        "stt_provider": config.STT_PROVIDER,
        "llm_provider": config.LLM_PROVIDER,
        "tts_provider": config.TTS_PROVIDER,
    }


@app.post("/api/start")
async def start_call(req: StartCallRequest | None = None):
    """Initializes a new Voice AI session ID without creating an unattached pipeline."""
    session_id = (req and req.session_id) or f"session_{uuid.uuid4().hex[:8]}"
    logger.info(f"[SESSION] Initializing session ID '{session_id}'")

    return {
        "session_id": session_id,
        "status": "initialized",
    }


@app.post("/api/webrtc/offer")
async def webrtc_offer(req: OfferRequest):
    """Handles WebRTC SDP offer/answer negotiation and attaches the real-time Pipecat pipeline."""
    session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"
    logger.info(f"[WEBRTC] Received SDP offer for session '{session_id}'")

    try:
        request = SmallWebRTCRequest(
            sdp=req.sdp,
            type=req.type,
            pc_id=req.pc_id,
        )

        async def on_connection(conn):
            logger.info(f"[WEBRTC] Connection established for peer: {conn.pc_id}")
            vad_analyzer = SileroVADAnalyzer(
                params=VADParams(
                    confidence=0.5,
                    start_secs=0.2,
                    stop_secs=0.35,
                    min_volume=0.05,
                )
            )

            transport = SmallWebRTCTransport(
                webrtc_connection=conn,
                params=TransportParams(
                    audio_in_enabled=True,
                    audio_out_enabled=True,
                    audio_in_vad_enabled=True,
                    vad_analyzer=vad_analyzer,
                ),
            )
            logger.info(f"[WEBRTC] SmallWebRTC transport created for session '{session_id}'")

            # Attach and start the Pipecat pipeline to this actual WebRTC connection
            await pipeline_manager.start_session(session_id, transport=transport, connection=conn)

        answer = await webrtc_request_handler.handle_web_request(request, on_connection)
        logger.info(f"[WEBRTC] SDP answer generated and sent for session '{session_id}'")
        return answer
    except Exception as e:
        logger.exception(f"[WEBRTC][ERROR] SDP offer negotiation failed: {e}")
        raise HTTPException(status_code=500, detail=f"WebRTC offer failed: {str(e)}")


@app.post("/api/stop")
async def stop_call(req: StopCallRequest):
    """Terminates an active Voice AI WebCall session."""
    logger.info(f"[SESSION] Received stop_call request for session '{req.session_id}'")
    success = await pipeline_manager.stop_session(req.session_id)
    if not success:
        logger.warning(f"[SESSION] Session '{req.session_id}' was not active or failed to stop.")
    return {"session_id": req.session_id, "status": "disconnected"}


@app.get("/api/status/{session_id}")
async def get_session_status(session_id: str):
    """Gets current status of a voice call session."""
    session = pipeline_manager.active_sessions.get(session_id)
    if not session:
        return {"session_id": session_id, "status": "idle"}
    return {
        "session_id": session_id,
        "status": session.get("status", "connected"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
