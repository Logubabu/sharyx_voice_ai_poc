from typing import Dict, Any, List, Optional
from pipecat.adapters.schemas.function_schema import FunctionSchema

from app.tools.base import BaseTool
from app.tools.web_search import WebSearchTool
from app.tools.executor import tool_executor
from app.utils.logging import logger


class ToolRegistry:
    """Central Tool Registry managing voice AI tools, schemas, and execution."""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        # Register WebSearchTool
        self.register_tool(WebSearchTool())

    def register_tool(self, tool: BaseTool):
        """Registers a BaseTool instance in the registry."""
        self.tools[tool.name] = tool
        logger.info(f"[TOOL-REGISTRY] Registered tool '{tool.name}' ({tool.description[:60]}...)")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def get_function_schemas(self) -> List[FunctionSchema]:
        """Returns list of FunctionSchema objects with attached handlers for LLMContext."""
        schemas = []
        for name, tool in self.tools.items():
            handler_func = self._create_handler(tool)
            schema = tool.get_schema(handler=handler_func)
            schemas.append(schema)
        return schemas

    def _create_handler(self, tool: BaseTool):
        async def _handler(function_name: str, tool_call_id: str, args: Dict[str, Any], llm: Any, context: Any, result_callback: Any):
            res = await tool_executor.execute_tool(tool, tool_call_id, args)
            await result_callback(res)
        return _handler

    def register_tools_on_llm(self, llm_service: Any):
        """Registers all tools directly on Pipecat LLM service instance."""
        for name, tool in self.tools.items():
            if hasattr(llm_service, "register_function"):
                handler = self._create_handler(tool)
                llm_service.register_function(name, handler, cancel_on_interruption=True)
                logger.info(f"[TOOL-REGISTRY] Registered function tool '{name}' on LLM service")


global_tool_registry = ToolRegistry()
