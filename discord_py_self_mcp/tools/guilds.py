import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="list_guilds",
    description="List all guilds the user is in",
    input_schema={
        "type": "object",
        "properties": {},
    }
)
async def list_guilds(arguments: dict):
    """List all guilds the authenticated user is a member of.

    This is an async MCP tool handler that returns the names and IDs of
    every guild in the client cache.

    Args:
        arguments: An empty dictionary (no parameters required).

    Returns:
        list[TextContent]: A single-element list with guild names and IDs
            separated by newlines, or an error message if the client is
            not ready.
    """
    if not client.is_ready():
        return [TextContent(type="text", text="Bot is not ready yet")]
    
    guilds = [f"{g.name} ({g.id})" for g in client.guilds]
    return [TextContent(type="text", text="\n".join(guilds))]

@registry.register(
    name="get_user_info",
    description="Get information about the current user",
    input_schema={
        "type": "object",
        "properties": {},
    }
)
async def get_user_info(arguments: dict):
    """Get information about the currently authenticated user.

    This is an async MCP tool handler that returns the username,
    discriminator, and ID of the self-bot user.

    Args:
        arguments: An empty dictionary (no parameters required).

    Returns:
        list[TextContent]: A single-element list with user info, or an
            error message if the client is not ready.
    """
    if not client.is_ready():
        return [TextContent(type="text", text="Bot is not ready yet")]
    
    user = client.user
    return [TextContent(type="text", text=f"User: {user.name}#{user.discriminator} ({user.id})")]
