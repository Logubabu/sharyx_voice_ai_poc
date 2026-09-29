import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import config
from app.pipeline import pipeline_manager
from app.transport import create_webrtc_transport
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
    """Pre-warms service adapters and logs provider configuration status."""
    logger.info("==================================================")
    logger.info("VOICE AI BACKEND STARTUP")
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
        logger.info("[CONFIG] Voice pipeline pre-warming complete. Backend ready for WebRTC connections.")
    except Exception as e:
        logger.warning(f"[CONFIG] Pre-warming notice: {e}")
    logger.info("==================================================")


from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequestHandler, SmallWebRTCRequest
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection

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


@app.get("/")
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/debug/providers")
@app.get("/api/config/status")
async def get_config_status():
    """Reports configuration status of required providers without revealing secrets."""
    return {
        "stt": {
            "provider": config.STT_PROVIDER,
            "configured": bool(config.SARVAM_API_KEY or config.STT_API_KEY),
        },
        "llm": {
            "provider": config.LLM_PROVIDER,
            "model": config.LLM_MODEL,
            "configured": bool(config.GEMINI_API_KEY or config.LLM_API_KEY),
        },
        "tts": {
            "provider": config.TTS_PROVIDER,
            "configured": bool(config.ELEVENLABS_API_KEY or config.TTS_API_KEY),
        },
    }


@app.post("/api/start")
async def start_call(req: StartCallRequest | None = None):
    """Initializes a new Voice AI logical session ID without starting an unattached pipeline."""
    session_id = (req and req.session_id) or f"session_{uuid.uuid4().hex[:8]}"
    logger.info(f"==================================================")
    logger.info(f"VOICE AI SESSION")
    logger.info(f"[SESSION] Created: {session_id}")

    return {
        "session_id": session_id,
        "status": "ready",
    }


@app.post("/api/webrtc/offer")
async def webrtc_offer(req: OfferRequest):
    """Handles WebRTC SDP offer/answer negotiation and creates the browser-connected Pipecat pipeline."""
    session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"
    logger.info(f"[WEBRTC] SDP offer received")

    try:
        request = SmallWebRTCRequest(
            sdp=req.sdp,
            type=req.type,
            pc_id=req.pc_id,
        )

        async def on_connection(connection: SmallWebRTCConnection):
            logger.info(f"[WEBRTC] Browser connection created: {connection.pc_id}")
            
            # Setup WebRTC disconnection listener to stop pipeline and free resources
            @connection.event_handler("closed")
            async def handle_webrtc_closed(conn: SmallWebRTCConnection):
                logger.info(f"[WEBRTC] Connection closed for pc_id: {conn.pc_id}. Stopping session '{session_id}'")
                await pipeline_manager.stop_session(session_id)

            transport = create_webrtc_transport(connection=connection, cfg=config)
            logger.info(f"[WEBRTC] Transport created")

            # Attach and start the Pipecat pipeline to this actual WebRTC connection
            await pipeline_manager.start_session(
                session_id=session_id,
                transport=transport,
                connection=connection,
            )
            logger.info(f"[WEBRTC] connected")

        answer = await webrtc_request_handler.handle_web_request(
            request=request,
            webrtc_connection_callback=on_connection,
        )
        logger.info(f"[WEBRTC] SDP answer returned to browser for session '{session_id}'")
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
    uvicorn.run("app.main:app", host="0.0.0.0", port="8000", reload=True)
