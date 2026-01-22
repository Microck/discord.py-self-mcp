from typing import Callable, Awaitable, Any
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import inspect

ToolHandler = Callable[[dict], Awaitable[list[TextContent | ImageContent | EmbeddedResource]]]

class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self.handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, description: str, input_schema: dict):
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
        return list(self.tools.values())

    async def call_tool(self, name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        handler = self.handlers.get(name)
        if not handler:
            raise ValueError(f"Tool {name} not found")
        return await handler(arguments)

registry = ToolRegistry()
