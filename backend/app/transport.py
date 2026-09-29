from typing import Any
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

from app.config import Config
from app.utils.logging import logger


def create_webrtc_transport(connection: SmallWebRTCConnection, cfg: Config) -> SmallWebRTCTransport:
    """Creates a SmallWebRTCTransport instance directly using the browser's active SmallWebRTCConnection."""
    logger.info(f"[WEBRTC] Creating SmallWebRTC Transport for connection: {connection.pc_id}")

    vad_analyzer = SileroVADAnalyzer(
        params=VADParams(
            confidence=0.5,
            start_secs=0.2,
            stop_secs=0.5,
            min_volume=0.01,
        )
    )

    return SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_vad_enabled=True,
            vad_analyzer=vad_analyzer,
        ),
    )
