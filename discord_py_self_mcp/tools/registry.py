from typing import Awaitable, Callable

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

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
            available_tools = ", ".join(sorted(self.handlers))
            raise ValueError(
                f"Unknown tool '{name}'. Available tools: {available_tools}"
            )
        return await handler(arguments)

registry = ToolRegistry()
