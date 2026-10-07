import pytest
from app.utils.audit import AuditLogger


def test_audit_logger_sanitization():
    raw_data = {
        "user_id": "usr_123",
        "api_key": "secret_gemini_key_xyz",
        "nested": {
            "password": "super_secret_pass",
            "normal_field": "public_data",
        },
    }

    sanitized = AuditLogger.sanitize_dict(raw_data)

    assert sanitized["user_id"] == "usr_123"
    assert sanitized["api_key"] == "***REDACTED***"
    assert sanitized["nested"]["password"] == "***REDACTED***"
    assert sanitized["nested"]["normal_field"] == "public_data"


def test_audit_logger_event():
    logger_instance = AuditLogger(max_memory_entries=10)

    entry = logger_instance.log_event(
        event="TEST_EVENT",
        category="security",
        session_id="sess_001",
        actor="system",
        action="unit_test",
        details={"query": "test query", "secret_token": "abc123secret"},
        status="SUCCESS",
        duration_ms=45.2,
    )

    assert entry["event"] == "TEST_EVENT"
    assert entry["category"] == "security"
    assert entry["session_id"] == "sess_001"
    assert entry["details"]["secret_token"] == "***REDACTED***"

    logs = logger_instance.get_recent_logs(limit=5)
    assert len(logs) == 1
    assert logs[0]["action"] == "unit_test"

    summary = logger_instance.get_summary()
    assert summary["total_audit_events"] == 1
    assert summary["storage"] == "console_only"
    assert summary["events_by_category"]["security"] == 1

