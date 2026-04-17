import asyncio
import os
import logging
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from discord_py_self_mcp.bot import client
from discord_py_self_mcp.tools import registry

# Suppress logging to stderr to avoid interfering with MCP stdio
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger("discord-selfbot-mcp")
# Silence discord library logging
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)

app = Server("discord-selfbot-mcp")


@app.list_tool()
async def list_tools() -> list[Tool]:
    """Return all registered MCP tool definitions.

    This is the MCP server handler for listing available tools.

    Returns:
        list[Tool]: A list of Tool objects representing all registered tools.
    """
    return registry.get_tool_definitions()


@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[TextContent | ImageContent | EmbeddedResource]:
    """Dispatch an MCP tool call to the appropriate registered handler.

    This is the MCP server handler for invoking tools by name.

    Args:
        name: The registered name of the tool to call.
        arguments: A dictionary of arguments to pass to the tool handler.

    Returns:
        list[TextContent | ImageContent | EmbeddedResource]: The result
            content returned by the tool handler.
    """
    return await registry.call_tool(name, arguments)


async def run_app():
    """Start the Discord self-bot client and the MCP stdio server.

    Reads the ``DISCORD_TOKEN`` environment variable, launches the Discord
    client as a background task, and then runs the MCP server over stdio.

    Raises:
        SystemExit: If ``DISCORD_TOKEN`` is not set.
    """
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        sys.stderr.write(
            "Error: DISCORD_TOKEN is not set. Configure it in your MCP client or run "
            "`discord-py-self-mcp-setup`.\n"
        )
        raise SystemExit(1)

    logger.info(f"Starting Discord connection...")
    logger.info(
        f"Token (masked): {token[:15]}...{token[-5:] if len(token) > 20 else token}"
    )

    # Start Discord client in background
    # We don't await it so it doesn't block the MCP server
    discord_task = asyncio.create_task(client.start(token))

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the discord-py-self-mcp console script.

    Runs the async application loop via ``asyncio.run``.
    """
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
