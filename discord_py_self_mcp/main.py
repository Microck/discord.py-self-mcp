import asyncio
import os
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from discord_py_self_mcp.bot import client
from discord_py_self_mcp.logging_utils import log_to_stderr, mask_secret
from discord_py_self_mcp.tools import registry

app = Server("discord-selfbot-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return registry.get_tool_definitions()


@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[TextContent | ImageContent | EmbeddedResource]:
    return await registry.call_tool(name, arguments)


async def run_app():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        sys.stderr.write(
            "Error: DISCORD_TOKEN is not set. Configure it in your MCP client or run "
            "`discord-py-self-mcp-setup`.\n"
        )
        raise SystemExit(1)

    log_to_stderr("[STARTUP] Starting Discord connection")
    log_to_stderr(f"[STARTUP] DISCORD_TOKEN: {mask_secret(token)}")

    # Start Discord client in background
    # We don't await it so it doesn't block the MCP server
    asyncio.create_task(client.start(token))

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
