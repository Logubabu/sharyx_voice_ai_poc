import asyncio
from typing import Any, Dict, Optional

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response import LLMFullResponseAggregator

from app.config import Config
from app.services.stt import create_stt_service
from app.services.llm import create_llm_service
from app.services.tts import create_tts_service
from app.transport import create_pipecat_transport
from app.utils.logging import logger


class VoicePipelineManager:
    """Manages the lifecycle of a real-time Voice AI pipeline session."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def start_session(self, session_id: str, room_url: str = "", token: Optional[str] = None, transport: Any = None):
        """Builds and starts the Pipecat real-time pipeline for a given session."""
        logger.info(f"Starting voice pipeline session '{session_id}'")

        # 1. Transport setup
        if not transport:
            transport = create_pipecat_transport(self.cfg, room_url=room_url, token=token)

        # 2. Services initialization via configurable adapters
        stt = create_stt_service(self.cfg)
        llm = create_llm_service(self.cfg)
        tts = create_tts_service(self.cfg)

        # 3. LLM Context with System Prompt
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

        # 4. Pipeline Assembly with VAD & Smart Turn Aggregation
        # Audio -> Transport -> STT -> User Aggregator -> LLM -> TTS -> Transport -> Assistant Aggregator
        pipeline_elements = [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]

        from pipecat.pipeline.task import PipelineTask
        pipeline = Pipeline(pipeline_elements)
        task_runner = PipelineTask(pipeline)
        runner = PipelineRunner()

        # Run pipeline task in a background task
        task = asyncio.create_task(runner.run(task_runner))

        self.active_sessions[session_id] = {
            "task": task,
            "runner": runner,
            "pipeline": pipeline,
            "transport": transport,
            "room_url": room_url,
            "status": "connected",
        }

        logger.info(f"Voice pipeline session '{session_id}' successfully started.")
        return self.active_sessions[session_id]

    async def stop_session(self, session_id: str):
        """Stops and cleans up a voice pipeline session."""
        session = self.active_sessions.pop(session_id, None)
        if not session:
            logger.warning(f"Session '{session_id}' not found for cleanup.")
            return False

        logger.info(f"Cleaning up voice pipeline session '{session_id}'")
        try:
            task = session.get("task")
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info(f"Session '{session_id}' stopped successfully.")
            return True
        except Exception as e:
            logger.error(f"Error during cleanup of session '{session_id}': {e}")
            return False


pipeline_manager = VoicePipelineManager(Config())
