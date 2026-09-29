import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import config
from app.pipeline import pipeline_manager
from app.transport import create_webrtc_room
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
    """Pre-warms service adapters and imports during server startup for sub-second response times."""
    logger.info("Pre-warming voice service pipeline adapters...")
    try:
        from app.services.stt import create_stt_service
        from app.services.llm import create_llm_service
        from app.services.tts import create_tts_service
        create_stt_service(config)
        create_llm_service(config)
        create_tts_service(config)
        logger.info("Voice pipeline pre-warming complete. /api/start ready for instant requests.")
    except Exception as e:
        logger.warning(f"Pre-warming warning: {e}")



from pipecat.transports.smallwebrtc.request_handler import SmallWebRTCRequestHandler, SmallWebRTCRequest

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
    return {
        "status": "healthy",
        "service": "Voice AI WebCall POC",
        "stt_provider": config.STT_PROVIDER,
        "llm_provider": config.LLM_PROVIDER,
        "tts_provider": config.TTS_PROVIDER,
    }


@app.post("/api/start")
async def start_call(req: StartCallRequest | None = None):
    """Starts a new Voice AI WebCall session."""
    session_id = (req and req.session_id) or f"session_{uuid.uuid4().hex[:8]}"
    logger.info(f"Received start_call request for session '{session_id}'")

    try:
        # Create open-source WebRTC session
        room_info = await create_webrtc_room(config)
        room_url = room_info["url"]
        token = room_info.get("token")

        # Start the Pipecat pipeline in background if not already active
        if session_id not in pipeline_manager.active_sessions:
            await pipeline_manager.start_session(session_id, room_url=room_url, token=token)

        return {
            "session_id": session_id,
            "room_url": room_url,
            "token": token,
            "status": "connected",
        }
    except Exception as e:
        logger.exception(f"Failed to start call for session '{session_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize voice service connection: {str(e)}")

@app.post("/api/webrtc/offer")
async def webrtc_offer(req: OfferRequest):
    """Handles WebRTC SDP offer/answer negotiation with browser client."""
    logger.info(f"Received WebRTC SDP offer for session '{req.session_id}'")
    try:
        request = SmallWebRTCRequest(
            sdp=req.sdp,
            type=req.type,
            pc_id=req.pc_id,
        )

        async def on_connection(conn):
            session_id = req.session_id or f"session_{uuid.uuid4().hex[:8]}"
            if session_id not in pipeline_manager.active_sessions:
                from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
                from pipecat.transports.base_transport import TransportParams
                transport = SmallWebRTCTransport(
                    webrtc_connection=conn,
                    params=TransportParams(audio_in_enabled=True, audio_out_enabled=True)
                )
                await pipeline_manager.start_session(session_id, transport=transport)

        answer = await webrtc_request_handler.handle_web_request(request, on_connection)
        return answer
    except Exception as e:
        logger.exception(f"WebRTC SDP offer negotiation failed: {e}")
        raise HTTPException(status_code=500, detail=f"WebRTC offer failed: {str(e)}")


@app.post("/api/stop")
async def stop_call(req: StopCallRequest):
    """Terminates an active Voice AI WebCall session."""
    logger.info(f"Received stop_call request for session '{req.session_id}'")
    success = await pipeline_manager.stop_session(req.session_id)
    if not success:
        logger.warning(f"Session '{req.session_id}' was not active or failed to stop.")
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
        "room_url": session.get("room_url"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)
