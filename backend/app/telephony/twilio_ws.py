import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.serializers.twilio import TwilioFrameSerializer

from app.config import config
from app.pipeline import pipeline_manager
from app.utils.logging import logger
from app.utils.audit import audit_logger


async def handle_twilio_audio_ws(websocket: WebSocket):
    """WebSocket handler for Twilio Media Streams (Inbound & Outbound Phone Calls).
    Connects Twilio G.711 mulaw audio bi-directionally to the Pipecat Voice AI Pipeline.
    """
    await websocket.accept()
    logger.info("[TWILIO-WS] Twilio WebSocket connection accepted")

    stream_sid = None
    call_sid = None

    try:
        # 1. Read initial Twilio metadata handshake messages to extract streamSid and callSid
        while not stream_sid:
            msg_str = await websocket.receive_text()
            msg_data = json.loads(msg_str)
            event_type = msg_data.get("event")

            if event_type == "start":
                start_data = msg_data.get("start", {})
                stream_sid = start_data.get("streamSid")
                call_sid = start_data.get("callSid")
                logger.info(f"[TWILIO-WS] Received start event - streamSid: '{stream_sid}', callSid: '{call_sid}'")
                break
            elif event_type == "connected":
                logger.info("[TWILIO-WS] Received connected event from Twilio. Awaiting start event...")

        if not stream_sid:
            stream_sid = f"stream_{id(websocket)}"
        if not call_sid:
            call_sid = f"twilio_call_{stream_sid[:8]}"

        audit_logger.log_event(
            event="TWILIO_MEDIA_STREAM_CONNECTED",
            category="telephony",
            actor="twilio",
            action="ws_connect",
            session_id=call_sid,
            details={"stream_sid": stream_sid, "call_sid": call_sid},
            status="SUCCESS",
        )

        # 2. Configure TwilioFrameSerializer with actual stream_sid
        serializer = TwilioFrameSerializer(
            stream_sid=stream_sid,
            call_sid=call_sid,
            account_sid=config.TWILIO_ACCOUNT_SID,
            auth_token=config.TWILIO_AUTH_TOKEN,
            params=TwilioFrameSerializer.InputParams(auto_hang_up=False),
        )

        # 3. Configure FastAPIWebsocketTransport
        transport_params = FastAPIWebsocketParams(
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        )

        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=transport_params,
        )

        # 4. Attach transport and launch Pipecat pipeline (8kHz telephony audio)
        session = await pipeline_manager.start_session(
            session_id=call_sid,
            transport=transport,
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
        )

        logger.info(f"[TWILIO-WS] Pipecat Voice AI pipeline active for call '{call_sid}' (streamSid: {stream_sid})")

        # 5. Await runner_task to keep WebSocket open until call finishes
        runner_task = session.get("runner_task")
        if runner_task:
            try:
                await runner_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(f"[TWILIO-WS] Twilio WebSocket disconnected for call '{call_sid or stream_sid}'")
    except Exception as e:
        logger.exception(f"[TWILIO-WS][ERROR] Exception in Twilio WebSocket handler: {e}")
    finally:
        if call_sid:
            await pipeline_manager.stop_session(call_sid)
            audit_logger.log_event(
                event="TWILIO_MEDIA_STREAM_DISCONNECTED",
                category="telephony",
                actor="twilio",
                action="ws_disconnect",
                session_id=call_sid,
                status="DISCONNECTED",
            )
