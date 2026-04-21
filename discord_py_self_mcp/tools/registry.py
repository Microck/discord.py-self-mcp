from typing import Callable, Awaitable
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

ToolHandler = Callable[[dict], Awaitable[list[TextContent | ImageContent | EmbeddedResource]]]

class ToolRegistry:
    """Registry mapping MCP tool names to their definitions and handlers."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self.handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, description: str, input_schema: dict):
        """Decorator that registers a function as an MCP tool handler."""
        def decorator(func: ToolHandler):
            self.tools[name] = Tool(
                name=name,
                description=description,
                inputSchema=input_schema
            )
            self.handlers[name] = func
            return func
        return decorator

    def get_tool_definitions(self) -> list[Tool]:
        """Return all registered tool definitions for MCP discovery."""
        return list(self.tools.values())

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Invoke a registered tool handler by name."""
        handler = self.handlers.get(name)
        if not handler:
            available_tools = ", ".join(sorted(self.handlers))
            raise ValueError(
                f"Unknown tool '{name}'. Available tools: {available_tools}"
            )
        return await handler(arguments)

registry = ToolRegistry()
