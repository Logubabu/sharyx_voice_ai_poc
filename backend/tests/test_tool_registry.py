import pytest
from unittest.mock import MagicMock, patch

from app.services.tools import VoiceToolRegistry


def test_tool_registry_web_search_enabled():
    with patch("app.config.config.WEB_SEARCH_ENABLED", True):
        registry = VoiceToolRegistry()
        schemas = registry.get_function_schemas()
        schema_names = [s.name for s in schemas]

        assert "web_search" in schema_names
        assert "web_fetch" in schema_names


def test_tool_registry_web_search_disabled():
    with patch("app.config.config.WEB_SEARCH_ENABLED", False):
        registry = VoiceToolRegistry()
        schemas = registry.get_function_schemas()
        schema_names = [s.name for s in schemas]

        assert "web_search" not in schema_names
        assert "web_fetch" not in schema_names


def test_llm_tool_registration():
    with patch("app.config.config.WEB_SEARCH_ENABLED", True):
        registry = VoiceToolRegistry()
        mock_llm_service = MagicMock()

        registry.register_tools_on_llm(mock_llm_service)

        # Check that register_function was called for web_search and web_fetch with cancel_on_interruption=True
        assert mock_llm_service.register_function.called
        
        registered_tool_args = [
            call_args[0][0].name if hasattr(call_args[0][0], 'name') else call_args[0][0]
            for call_args in mock_llm_service.register_function.call_args_list
        ]
        
        assert "web_search" in registered_tool_args
        assert "web_fetch" in registered_tool_args

        # Ensure cancel_on_interruption=True was passed in kwargs
        for call_args in mock_llm_service.register_function.call_args_list:
            assert call_args[1].get("cancel_on_interruption") is True
