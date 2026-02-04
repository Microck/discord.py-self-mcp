import asyncio
import os
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from discord_py_self_mcp.bot import client
from discord_py_self_mcp.tools import registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord-selfbot-mcp")

app = Server("discord-selfbot-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return registry.get_tool_definitions()

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
    return await registry.call_tool(name, arguments)

async def run_app():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        return

    logger.info(f"Starting Discord connection...")
    logger.info(f"Token (masked): {token[:15]}...{token[-5:] if len(token) > 20 else token}")

    # Start Discord client in background
    # We don't await it so it doesn't block the MCP server
    discord_task = asyncio.create_task(client.start(token))

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

def main():
    asyncio.run(run_app())

if __name__ == "__main__":
    main()
