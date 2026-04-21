import asyncio
import os
import logging
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from discord_py_self_mcp.bot import client
from discord_py_self_mcp.logging_utils import mask_secret
from discord_py_self_mcp.tools import registry

# Suppress logging to stderr to avoid interfering with MCP stdio
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("discord-selfbot-mcp")
# Silence discord library logging
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)

app = Server("discord-selfbot-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available MCP tools."""
    return registry.get_tool_definitions()


@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Dispatch an MCP tool call by name with the given arguments."""
    return await registry.call_tool(name, arguments)


async def run_app():
    """Start the Discord client and MCP stdio server."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        sys.stderr.write(
            "Error: DISCORD_TOKEN is not set. Configure it in your MCP client or run "
            "`discord-py-self-mcp-setup`.\n"
        )
        raise SystemExit(1)

    logger.info("Starting Discord connection...")
    logger.info(
        f"Token (masked): {mask_secret(token)}"
    )

    # Start Discord client in background
    # We don't await it so it doesn't block the MCP server
    asyncio.create_task(client.start(token))

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the discord-py-self-mcp package."""
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
