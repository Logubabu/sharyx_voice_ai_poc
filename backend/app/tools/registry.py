from typing import Dict, Any, List, Optional
from pipecat.adapters.schemas.function_schema import FunctionSchema

from app.tools.base import BaseTool
from app.tools.web_search.tool import WebSearchTool
from app.utils.logging import logger


class ToolRegistry:
    """Central Tool Registry holding tool definitions and generating LLM function schemas."""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Registers core tools into the registry."""
        self.register_tool(WebSearchTool())

    def register_tool(self, tool: BaseTool):
        """Registers a BaseTool instance in the registry."""
        self.tools[tool.name] = tool
        logger.info(f"[TOOL-REGISTRY] Registered tool '{tool.name}' ({tool.description[:60]}...)")

    def unregister_tool(self, name: str):
        """Removes a tool from the registry."""
        if name in self.tools:
            del self.tools[name]
            logger.info(f"[TOOL-REGISTRY] Unregistered tool '{name}'")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Gets a registered tool by name."""
        return self.tools.get(name)

    def get_function_schemas(self, enable_web_search: bool = True, router: Any = None) -> List[FunctionSchema]:
        """Returns list of FunctionSchema objects with attached handlers for LLMContext."""
        from app.tools.router import tool_router
        active_router = router or tool_router
        schemas = []
        for name, tool in self.tools.items():
            if name == "web_search" and not enable_web_search:
                continue

            handler_func = active_router.create_handler(tool) if active_router else None
            schema = tool.get_schema(handler=handler_func)
            schemas.append(schema)
        return schemas

    def register_tools_on_llm(self, llm_service: Any, enable_web_search: bool = True, router: Any = None):
        """Registers function handlers directly on Pipecat LLM service instance."""
        for name, tool in self.tools.items():
            if name == "web_search" and not enable_web_search:
                logger.info(f"[TOOL-REGISTRY] Skipping web search tool '{name}' (web_search disabled)")
                continue

            if hasattr(llm_service, "register_function"):
                handler = router.create_handler(tool) if router else None
                if handler:
                    llm_service.register_function(name, handler, cancel_on_interruption=True)
                    logger.info(f"[TOOL-REGISTRY] Registered function tool '{name}' on LLM service")


global_tool_registry = ToolRegistry()
