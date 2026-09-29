import asyncio
import time
from typing import Any, Dict, Optional

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from app.config import Config
from app.services.stt import create_stt_service
from app.services.llm import create_llm_service
from app.services.tts import create_tts_service
from app.utils.logging import logger


class DiagnosticEventProcessor(FrameProcessor):
    """Intercepts pipeline frames to produce structured diagnostic logs and real-time DataChannel events."""

    def __init__(self, connection: Any = None):
        super().__init__()
        self.connection = connection
        self.current_ai_response = ""

    def _send_app_message(self, data: dict):
        if self.connection and hasattr(self.connection, "send_app_message"):
            try:
                self.connection.send_app_message(data)
            except Exception as e:
                logger.warning(f"[AUDIO] Failed to send app message over data channel: {e}")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            logger.info("[STT] Audio received [User started speaking]")
            self._send_app_message({"type": "state", "state": "listening"})

        elif isinstance(frame, TranscriptionFrame):
            logger.info("[STT] Transcription started")
            logger.info(f"[STT] User text: '{frame.text}'")
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
                    logger.info(f"[LLM] Request: '{text_snippet}'")
                    self._send_app_message({"type": "state", "state": "speaking"})
                self.current_ai_response += frame.text
                logger.info(f"[LLM] Response chunk: '{text_snippet}'")
                self._send_app_message({
                    "type": "transcript",
                    "sender": "ai",
                    "text": self.current_ai_response,
                    "timestamp": time.strftime("%I:%M %p"),
                })

        elif isinstance(frame, TTSStartedFrame):
            logger.info("[TTS] Request received [TTS Started]")
            logger.info("[TTS] Generating audio")
            logger.info("[AUDIO] Sending audio to browser")
            self._send_app_message({"type": "state", "state": "speaking"})

        elif isinstance(frame, TTSStoppedFrame):
            logger.info("[TTS] Audio generated [TTS Finished]")
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
        """Builds and starts the Pipecat real-time pipeline attached to a WebRTC transport."""
        logger.info(f"[PIPELINE] Building voice pipeline for session '{session_id}'")

        # 1. Services initialization via configurable adapters
        stt = create_stt_service(self.cfg)
        llm = create_llm_service(self.cfg)
        tts = create_tts_service(self.cfg)

        # 2. LLM Context with System Prompt
        context = LLMContext(
            messages=[
                {"role": "system", "content": self.cfg.SYSTEM_PROMPT}
            ]
        )

        from pipecat.processors.aggregators.llm_response_universal import (
            LLMUserAggregator,
            LLMAssistantAggregator,
        )

        user_aggregator = LLMUserAggregator(context)
        assistant_aggregator = LLMAssistantAggregator(context)
        diagnostic_processor = DiagnosticEventProcessor(connection=connection)

        # 3. Pipeline Assembly: Transport Input -> STT -> User Aggregator -> LLM -> Diagnostic -> TTS -> Transport Output -> Assistant Aggregator
        pipeline_elements = [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            diagnostic_processor,
            tts,
            transport.output(),
            assistant_aggregator,
        ]

        from pipecat.pipeline.task import PipelineTask
        pipeline = Pipeline(pipeline_elements)
        task_runner = PipelineTask(pipeline)
        runner = PipelineRunner()

        # Run pipeline task in background
        task = asyncio.create_task(runner.run(task_runner))

        self.active_sessions[session_id] = {
            "task": task,
            "runner": runner,
            "pipeline": pipeline,
            "transport": transport,
            "connection": connection,
            "status": "connected",
        }

        logger.info(f"[PIPELINE] Voice pipeline for session '{session_id}' successfully started.")
        return self.active_sessions[session_id]

    async def stop_session(self, session_id: str) -> bool:
        """Stops and cleans up a voice pipeline session."""
        session = self.active_sessions.pop(session_id, None)
        if not session:
            logger.warning(f"[SESSION] Session '{session_id}' not found for cleanup.")
            return False

        logger.info(f"[SESSION] Cleaning up voice pipeline session '{session_id}'")
        try:
            task = session.get("task")
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"[SESSION] Session task for '{session_id}' cancelled cleanly.")
            logger.info(f"[SESSION] Session '{session_id}' stopped successfully.")
            return True
        except Exception as e:
            logger.exception(f"[SESSION][ERROR] Error during cleanup of session '{session_id}': {e}")
            return False


pipeline_manager = VoicePipelineManager(Config())
