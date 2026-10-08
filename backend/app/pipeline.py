import asyncio
import time
from typing import Any, Dict, Optional

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    AudioRawFrame,
    ErrorFrame,
    Frame,
    InputAudioRawFrame,
    LLMRunFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    TTSAudioRawFrame,
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
from app.services.audio_processor import NoiseCancellationFrameProcessor, audio_processor_factory
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

    def __init__(self, connection: Any = None, session_id: str = "default_session"):
        super().__init__()
        self.connection = connection
        self.session_id = session_id
        self.current_ai_response = ""

    def _send_app_message(self, data: dict):
        if self.connection and hasattr(self.connection, "send_app_message"):
            try:
                self.connection.send_app_message(data)
            except Exception as e:
                logger.warning(f"[AUDIO] Notice sending app message over data channel: {e}")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            logger.info("[VAD] user started speaking (barge-in interruption detected)")
            from app.tools.router import tool_router
            cancelled_count = tool_router.cancel_pending_tools(self.session_id)
            tool_router.reset_turn(self.session_id)
            if cancelled_count > 0:
                logger.info(f"[PIPELINE][BARGE-IN] Cancelled {cancelled_count} in-flight tool tasks due to user interruption")
            self._send_app_message({"type": "interruption"})
            self._send_app_message({"type": "state", "state": "listening"})
            self.current_ai_response = ""

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

        elif isinstance(frame, ErrorFrame):
            processor = getattr(frame, "processor", "pipeline")
            error_msg = getattr(frame, "error", str(frame))
            logger.error(f"[PIPELINE][ERROR] [{processor}] {error_msg}")

        await self.push_frame(frame, direction)


class TTSMonitor(FrameProcessor):
    """Monitors TTS output frames immediately after the TTS service."""

    def __init__(self, connection: Any = None):
        super().__init__()
        self.connection = connection
        self.tts_frame_count = 0

    def _send_app_message(self, data: dict):
        if self.connection and hasattr(self.connection, "send_app_message"):
            try:
                self.connection.send_app_message(data)
            except Exception as e:
                logger.warning(f"[AUDIO] Notice sending app message over data channel: {e}")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TTSStartedFrame):
            logger.info("[TTS] Started")
            self.tts_frame_count = 0
            self._send_app_message({"type": "state", "state": "speaking"})

        elif isinstance(frame, TTSAudioRawFrame):
            self.tts_frame_count += 1
            if self.tts_frame_count == 1 or self.tts_frame_count % 25 == 0:
                sample_rate = getattr(frame, "sample_rate", "unknown")
                logger.info(f"[TTS] audio frames: {self.tts_frame_count} (sample_rate: {sample_rate})")

        elif isinstance(frame, TTSStoppedFrame):
            logger.info(f"[TTS] Stopped, frames: {self.tts_frame_count}")
            if self.tts_frame_count == 0:
                logger.error("[TTS][FATAL] ZERO audio frames produced")
                self._send_app_message({"type": "error", "message": "TTS produced no audio"})
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
        audio_in_sample_rate: int = 16000,
        audio_out_sample_rate: int = 24000,
        is_webcall: bool = True,
    ):
        """Builds and starts the Pipecat real-time pipeline attached to a transport."""
        if transport is None:
            logger.error("[PIPELINE][FATAL] start_session called without a connected transport!")
            raise ValueError("A connected SmallWebRTC transport is required")

        logger.info(f"[PIPELINE] Creating STT")
        stt = create_stt_service(self.cfg)

        logger.info(f"[PIPELINE] Creating LLM (is_webcall={is_webcall})")
        llm = create_llm_service(self.cfg, is_webcall=is_webcall)
        setattr(llm, "session_id", session_id)

        logger.info(f"[PIPELINE] Creating TTS")
        tts = create_tts_service(self.cfg)

        from app.tools.registry import global_tool_registry
        from app.tools.router import tool_router

        tool_calling_enabled = self.cfg.WEBCALL_TOOL_CALLING_ENABLED if is_webcall else False
        web_search_enabled = self.cfg.WEBCALL_WEB_SEARCH_ENABLED if is_webcall else False

        if tool_calling_enabled:
            tools = global_tool_registry.get_function_schemas(enable_web_search=web_search_enabled, router=tool_router)
            logger.info(f"[PIPELINE] Tools configured for WebCall (count={len(tools)}, web_search={web_search_enabled})")
        else:
            tools = []
            logger.info(f"[PIPELINE] Tool calling disabled for session '{session_id}' (is_webcall={is_webcall})")

        current_date_info = time.strftime("%A, %B %d, %Y (%I:%M %p)")
        system_content = f"Today's Date and Time: {current_date_info}\n\n{self.cfg.SYSTEM_PROMPT}"

        context = LLMContext(
            messages=[
                {"role": "system", "content": system_content}
            ],
            tools=tools,
        )

        vad_analyzer = SileroVADAnalyzer(
            params=VADParams(
                confidence=0.6,
                start_secs=0.2,
                stop_secs=0.3,
                min_volume=0.1,
            )
        )

        aggregators = LLMContextAggregatorPair(
            context,
            user_params=LLMUserAggregatorParams(vad_analyzer=vad_analyzer),
        )

        audio_debug = AudioDebugProcessor()
        noise_cancellation_processor = NoiseCancellationFrameProcessor(connection=connection)
        diagnostic_processor = DiagnosticEventProcessor(connection=connection, session_id=session_id)
        tts_monitor = TTSMonitor(connection=connection)

        logger.info(f"[PIPELINE] Pipeline created with NoiseCancellationFrameProcessor")

        # Pipeline order: transport.input(), audio_debug, noise_cancellation_processor, stt, aggregators.user(), llm, aggregators.assistant(), diagnostic_processor, tts, tts_monitor, transport.output()
        pipeline_elements = [
            transport.input(),
            audio_debug,
            noise_cancellation_processor,
            stt,
            aggregators.user(),
            llm,
            aggregators.assistant(),
            diagnostic_processor,
            tts,
            tts_monitor,
            transport.output(),
        ]

        pipeline = Pipeline(pipeline_elements)
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=audio_in_sample_rate,
                audio_out_sample_rate=audio_out_sample_rate,
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

        # Add initial greeting prompt so context is valid for Gemini (has non-system message)
        context.add_message({"role": "user", "content": "Greet the user in one short sentence."})

        async def trigger_initial_greeting():
            if connection:
                # Wait for WebRTC connection to reach connected state before sending initial audio
                for _ in range(25):
                    if hasattr(connection, "is_connected") and connection.is_connected():
                        break
                    await asyncio.sleep(0.1)
            await task.queue_frame(LLMRunFrame())

        asyncio.create_task(trigger_initial_greeting())

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
