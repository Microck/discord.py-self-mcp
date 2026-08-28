import asyncio
import argparse
from contextlib import asynccontextmanager
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


async def start_discord_client() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        sys.stderr.write(
            "Error: DISCORD_TOKEN is not set. Configure it in your MCP client or run "
            "`discord-py-self-mcp-setup`.\n"
        )
        raise SystemExit(1)

    log_to_stderr("[STARTUP] Starting Discord connection")
    log_to_stderr(f"[STARTUP] DISCORD_TOKEN: {mask_secret(token)}")

    # Do not await the long-lived gateway client: it runs alongside the MCP
    # transport for the lifetime of this process.
    asyncio.create_task(client.start(token))


async def run_stdio() -> None:
    await start_discord_client()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


async def run_app() -> None:
    """Backward-compatible entry point for the original stdio server."""
    await run_stdio()


def create_streamable_http_app():
    """Build a localhost-only Streamable HTTP MCP endpoint at /mcp."""
    from mcp.server.fastmcp.server import StreamableHTTPASGIApp
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.routing import Route

    session_manager = StreamableHTTPSessionManager(app=app)
    http_app = StreamableHTTPASGIApp(session_manager)

    @asynccontextmanager
    async def lifespan(_starlette_app):
        await start_discord_client()
        async with session_manager.run():
            yield

    return Starlette(routes=[Route("/mcp", endpoint=http_app)], lifespan=lifespan)


async def run_streamable_http(host: str, port: int) -> None:
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(
            create_streamable_http_app(), host=host, port=port, log_level="info"
        )
    )
    await server.serve()


def main():
    parser = argparse.ArgumentParser(description="Discord self-account MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "7781")))
    options = parser.parse_args()

    if options.transport == "streamable-http":
        asyncio.run(run_streamable_http(options.host, options.port))
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
