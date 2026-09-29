from typing import Dict, Any, Optional
from app.config import Config
from app.utils.logging import logger


async def create_webrtc_room(cfg: Config) -> Dict[str, Any]:
    """Creates a local open-source WebRTC room session.
    100% free and open-source, requiring zero third-party accounts or paid APIs.
    """
    logger.info("Initializing free open-source local WebRTC room session.")
    return {
        "url": f"http://{cfg.HOST}:{cfg.PORT}/webrtc",
        "token": "local-open-source-token",
    }


def create_pipecat_transport(cfg: Config, room_url: str, token: Optional[str] = None):
    """Creates and returns the open-source SmallWebRTC Transport adapter with Voice Activity Detection (VAD)."""
    logger.info("Initializing Open-Source SmallWebRTC Transport with tuned VAD noise suppression")
    try:
        from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
        from pipecat.transports.base_transport import TransportParams
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.audio.vad.vad_analyzer import VADParams

        # Configure Silero VAD for fast speech detection and silence/noise rejection
        vad_analyzer = SileroVADAnalyzer(
            params=VADParams(
                confidence=0.5,
                start_secs=0.2,
                stop_secs=0.35,
                min_volume=0.05,
            )
        )

        conn = SmallWebRTCConnection(ice_servers=[])
        return SmallWebRTCTransport(
            webrtc_connection=conn,
            params=TransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_vad_enabled=True,
                vad_analyzer=vad_analyzer,
            ),
        )
    except Exception as err:
        logger.error(f"Failed to initialize open-source WebRTC transport: {err}")
        raise RuntimeError(f"No available WebRTC transport found: {err}") from err
