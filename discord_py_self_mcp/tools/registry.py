from typing import Callable, Awaitable, Any
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import inspect

ToolHandler = Callable[[dict], Awaitable[list[TextContent | ImageContent | EmbeddedResource]]]

class ToolRegistry:
    def __init__(self):
        """Initialize an empty tool registry."""
        self.tools: dict[str, Tool] = {}
        self.handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, description: str, input_schema: dict):
        """Decorator that registers a function as an MCP tool handler.

        Args:
            name: The unique tool name exposed over MCP.
            description: A human-readable description of the tool.
            input_schema: A JSON Schema dictionary describing the tool's
                expected input.

        Returns:
            Callable: The original function, unmodified.
        """
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
        """Return all registered tool definitions.

        Returns:
            list[Tool]: A list of MCP Tool objects.
        """
        return list(self.tools.values())

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Dispatch a tool call to the registered handler.

        Args:
            name: The registered tool name.
            arguments: The arguments to pass to the tool handler.

        Returns:
            list[TextContent | ImageContent | EmbeddedResource]: The
                result content returned by the tool handler.

        Raises:
            ValueError: If the tool name is not registered.
        """
        handler = self.handlers.get(name)
        if not handler:
            available_tools = ", ".join(sorted(self.handlers))
            raise ValueError(
                f"Unknown tool '{name}'. Available tools: {available_tools}"
            )
        return await handler(arguments)

registry = ToolRegistry()
