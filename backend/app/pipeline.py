import asyncio
import time
from typing import Any, Dict, Optional

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    InputAudioRawFrame,
    LLMRunFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.config import Config
from app.services.stt import create_stt_service
from app.services.llm import create_llm_service
from app.services.tts import create_tts_service
from app.utils.logging import logger


class AudioDebugProcessor(FrameProcessor):
    """Temporary audio debug processor that counts incoming audio frames from WebRTC and logs periodically."""

    def __init__(self):
        super().__init__()
        self.frame_count = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            self.frame_count += 1
            if self.frame_count % 50 == 0 or self.frame_count == 1:
                logger.info(f"[AUDIO-IN] received {self.frame_count} audio frames")
        await self.push_frame(frame, direction)


class DiagnosticEventProcessor(FrameProcessor):
    """Intercepts pipeline frames to produce structured diagnostic logs and real-time DataChannel events."""

    def __init__(self, connection: Any = None):
        super().__init__()
        self.connection = connection
        self.current_ai_response = ""
        self.tts_frame_count = 0

    def _send_app_message(self, data: dict):
        if self.connection and hasattr(self.connection, "send_app_message"):
            try:
                self.connection.send_app_message(data)
            except Exception as e:
                logger.warning(f"[AUDIO] Notice sending app message over data channel: {e}")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            logger.info("[VAD] user started speaking")
            self._send_app_message({"type": "state", "state": "listening"})

        elif isinstance(frame, UserStoppedSpeakingFrame):
            logger.info("[VAD] user stopped speaking")

        elif isinstance(frame, TranscriptionFrame):
            logger.info("[STT] Processing user audio")
            logger.info(f"[STT] Transcript: {frame.text}")
            self._send_app_message({
                "type": "transcript",
                "sender": "user",
                "text": frame.text,
                "timestamp": time.strftime("%I:%M %p"),
            })
            self._send_app_message({"type": "state", "state": "processing"})
            self.current_ai_response = ""

        elif isinstance(frame, TextFrame):
            text_snippet = frame.text.strip()
            if text_snippet:
                if not self.current_ai_response:
                    logger.info(f"[LLM] Input: {text_snippet}")
                    self._send_app_message({"type": "state", "state": "speaking"})
                self.current_ai_response += frame.text
                logger.info(f"[LLM] Output: {text_snippet}")
                self._send_app_message({
                    "type": "transcript",
                    "sender": "ai",
                    "text": self.current_ai_response,
                    "timestamp": time.strftime("%I:%M %p"),
                })

        elif isinstance(frame, TTSStartedFrame):
            logger.info("[TTS] Started")
            self.tts_frame_count = 0
            self._send_app_message({"type": "state", "state": "speaking"})

        elif isinstance(frame, AudioRawFrame) and not isinstance(frame, InputAudioRawFrame):
            self.tts_frame_count += 1
            if self.tts_frame_count % 20 == 0 or self.tts_frame_count == 1:
                logger.info(f"[TTS] audio frame received [frames: {self.tts_frame_count}]")
                logger.info(f"[AUDIO-OUT] sending audio frame [frames: {self.tts_frame_count}]")

        elif isinstance(frame, TTSStoppedFrame):
            logger.info(f"[TTS] Audio generated [total frames: {self.tts_frame_count}]")
            self._send_app_message({"type": "state", "state": "listening"})

        await self.push_frame(frame, direction)


class VoicePipelineManager:
    """Manages the lifecycle of a real-time Voice AI pipeline session."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def start_session(
        self,
        session_id: str,
        transport: Any,
        connection: Any = None,
    ):
        """Builds and starts the Pipecat real-time pipeline attached strictly to a WebRTC transport."""
        if transport is None:
            logger.error("[PIPELINE][FATAL] start_session called without a connected transport!")
            raise ValueError("A connected SmallWebRTC transport is required")

        logger.info(f"[PIPELINE] Creating STT")
        stt = create_stt_service(self.cfg)

        logger.info(f"[PIPELINE] Creating LLM")
        llm = create_llm_service(self.cfg)

        logger.info(f"[PIPELINE] Creating TTS")
        tts = create_tts_service(self.cfg)

        context = LLMContext(
            messages=[
                {"role": "system", "content": self.cfg.SYSTEM_PROMPT}
            ]
        )

        vad_analyzer = SileroVADAnalyzer(
            params=VADParams(
                confidence=0.6,
                start_secs=0.2,
                stop_secs=0.6,
                min_volume=0.3,
            )
        )

        aggregators = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(vad_analyzer=vad_analyzer),
        )

        audio_debug = AudioDebugProcessor()
        diagnostic_processor = DiagnosticEventProcessor(connection=connection)

        logger.info(f"[PIPELINE] Pipeline created")

        # Pipeline order: transport.input(), audio_debug, stt, aggregators.user(), llm, diagnostic_processor, tts, transport.output(), aggregators.assistant()
        pipeline_elements = [
            transport.input(),
            audio_debug,
            stt,
            aggregators.user(),
            llm,
            diagnostic_processor,
            tts,
            transport.output(),
            aggregators.assistant(),
        ]

        pipeline = Pipeline(pipeline_elements)
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=16000,
                audio_out_sample_rate=24000,
                enable_metrics=True,
            ),
        )
        runner = PipelineRunner()

        # Run pipeline task in background
        runner_task = asyncio.create_task(runner.run(task))

        self.active_sessions[session_id] = {
            "task": task,
            "runner_task": runner_task,
            "runner": runner,
            "pipeline": pipeline,
            "transport": transport,
            "connection": connection,
            "session_id": session_id,
            "status": "connected",
        }

        logger.info(f"[PIPELINE] Pipeline started")

        # Queue LLMRunFrame so bot speaks first on connect
        await task.queue_frame(LLMRunFrame())

        return self.active_sessions[session_id]

    async def stop_session(self, session_id: str) -> bool:
        """Stops and cleans up a voice pipeline session."""
        session = self.active_sessions.pop(session_id, None)
        if not session:
            logger.warning(f"[SESSION] Session '{session_id}' not found for cleanup.")
            return False

        logger.info(f"[SESSION] Cleaning up voice pipeline session '{session_id}'")
        try:
            task: PipelineTask = session.get("task")
            if task:
                await task.cancel()
                logger.info(f"[SESSION] PipelineTask for '{session_id}' cancelled cleanly.")

            runner_task = session.get("runner_task")
            if runner_task and not runner_task.done():
                runner_task.cancel()
                try:
                    await runner_task
                except asyncio.CancelledError:
                    pass

            logger.info(f"[SESSION] Session '{session_id}' stopped successfully.")
            return True
        except Exception as e:
            logger.exception(f"[SESSION][ERROR] Error during cleanup of session '{session_id}': {e}")
            return False


pipeline_manager = VoicePipelineManager(Config())
