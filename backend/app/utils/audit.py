import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.utils.logging import logger


class AuditLogger:
    """Console-only audit logger tracking security events, tool calls, WebRTC sessions, and system configuration changes."""

    def __init__(self, max_memory_entries: int = 500):
        self.max_memory_entries = max_memory_entries
        self.memory_buffer: List[Dict[str, Any]] = []

    @staticmethod
    def sanitize_dict(data: Any) -> Any:
        """Recursively sanitizes sensitive parameters such as API keys, tokens, and authorization headers."""
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                lower_key = str(k).lower()
                if any(sec in lower_key for sec in ["api_key", "secret", "token", "password", "auth", "credential", "cookie"]):
                    sanitized[k] = "***REDACTED***"
                else:
                    sanitized[k] = AuditLogger.sanitize_dict(v)
            return sanitized
        elif isinstance(data, list):
            return [AuditLogger.sanitize_dict(item) for item in data]
        elif isinstance(data, str) and len(data) > 500:
            return data[:500] + " [Truncated for audit log]"
        return data

    def log_event(
        self,
        event: str,
        category: str,
        session_id: Optional[str] = None,
        actor: str = "system",
        action: str = "",
        details: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
        duration_ms: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Prints a structured audit event to standard output/console and updates in-memory buffer."""
        iso_timestamp = datetime.now(timezone.utc).isoformat()
        
        sanitized_details = self.sanitize_dict(details or {})

        audit_entry = {
            "timestamp": iso_timestamp,
            "event": event,
            "category": category,
            "session_id": session_id or "global",
            "actor": actor,
            "action": action,
            "status": status,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "details": sanitized_details,
        }

        # Print formatted audit log entry directly to console
        dur_str = f" ({duration_ms:.1f}ms)" if duration_ms is not None else ""
        details_str = f" details={json.dumps(sanitized_details)}" if sanitized_details else ""
        logger.info(
            f"[AUDIT][{category.upper()}][{status}] event={event} action='{action}' session={session_id or 'global'}{dur_str}{details_str}"
        )

        # In-memory buffer
        self.memory_buffer.append(audit_entry)
        if len(self.memory_buffer) > self.max_memory_entries:
            self.memory_buffer.pop(0)

        return audit_entry

    def get_recent_logs(self, limit: int = 50, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns recent in-memory audit logs, optionally filtered by category."""
        logs = self.memory_buffer
        if category:
            logs = [entry for entry in logs if entry.get("category") == category]
        return logs[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistical summary of recorded audit events."""
        categories: Dict[str, int] = {}
        statuses: Dict[str, int] = {}
        events: Dict[str, int] = {}

        for entry in self.memory_buffer:
            cat = entry.get("category", "unknown")
            st = entry.get("status", "unknown")
            ev = entry.get("event", "unknown")

            categories[cat] = categories.get(cat, 0) + 1
            statuses[st] = statuses.get(st, 0) + 1
            events[ev] = events.get(ev, 0) + 1

        return {
            "total_audit_events": len(self.memory_buffer),
            "storage": "console_only",
            "events_by_category": categories,
            "events_by_status": statuses,
            "top_events": events,
        }


audit_logger = AuditLogger()
