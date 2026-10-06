import asyncio
from app.utils.logging import logger

def apply_aioice_patches():
    """Patches aioice and asyncio datagram transport to prevent closed-socket AttributeError tracebacks during WebRTC disconnects."""
    try:
        import aioice.stun
        if hasattr(aioice.stun.Transaction, "_Transaction__retry"):
            original_retry = aioice.stun.Transaction._Transaction__retry

            def safe_retry(self):
                try:
                    protocol = getattr(self, "_Transaction__protocol", None)
                    if protocol:
                        transport = getattr(protocol, "transport", None)
                        if transport is None or getattr(transport, "_sock", None) is None or getattr(transport, "_loop", None) is None:
                            return
                    original_retry(self)
                except (AttributeError, RuntimeError, OSError):
                    pass

            aioice.stun.Transaction._Transaction__retry = safe_retry
            logger.info("[PATCH] Patched aioice.stun.Transaction.__retry for safe socket teardown.")
    except Exception as e:
        logger.warning(f"[PATCH] Notice patching aioice: {e}")

    try:
        from asyncio.selector_events import _SelectorDatagramTransport
        original_fatal_error = _SelectorDatagramTransport._fatal_error

        def safe_fatal_error(self, exc, message='Fatal error on datagram transport'):
            if getattr(self, "_loop", None) is None or getattr(self, "_sock", None) is None:
                return
            try:
                original_fatal_error(self, exc, message)
            except (AttributeError, RuntimeError):
                pass

        _SelectorDatagramTransport._fatal_error = safe_fatal_error
        logger.info("[PATCH] Patched asyncio._SelectorDatagramTransport._fatal_error for safe loop shutdown.")
    except Exception as e:
        logger.warning(f"[PATCH] Notice patching asyncio datagram transport: {e}")


def setup_asyncio_exception_handler():
    """Configures global asyncio exception handler to suppress closed STUN/UDP socket warnings."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()

    def handle_exception(loop, context):
        exception = context.get("exception")
        message = context.get("message", "")
        exc_str = str(exception) if exception else ""
        if isinstance(exception, AttributeError) and ("sendto" in exc_str or "call_exception_handler" in exc_str):
            # Suppress teardown race condition in closed STUN sockets
            return
        if "Transaction.__retry" in message or "sendto" in message:
            return
        loop.default_exception_handler(context)

    loop.set_exception_handler(handle_exception)
    logger.info("[PATCH] Global asyncio exception handler configured.")
