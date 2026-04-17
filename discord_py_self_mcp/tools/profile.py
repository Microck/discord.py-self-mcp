import discord
from mcp.types import TextContent
from .registry import registry
from ..bot import client

@registry.register(
    name="edit_profile",
    description="Edit user profile (bio, accent color, etc)",
    input_schema={
        "type": "object",
        "properties": {
            "bio": {"type": "string"},
            "accent_color": {"type": "integer", "description": "Integer color value"},
            "password": {"type": "string", "description": "Required to change some settings"}
        }
    }
)
async def edit_profile(arguments: dict):
    """Edit the self-bot user's profile.

    This is an async MCP tool handler that updates profile fields such as
    bio and accent color. Changing username or email requires the
    ``password`` parameter.

    Args:
        arguments: A dictionary with optional keys ``bio`` (str),
            ``accent_color`` (int), and ``password`` (str).

    Returns:
        list[TextContent]: A single-element list with a confirmation or
            error message.
    """
    try:
        # discord.py-self client.user.edit()
        kwargs = {}
        if "bio" in arguments:
            kwargs["bio"] = arguments["bio"]
        if "accent_color" in arguments:
            kwargs["accent_colour"] = arguments["accent_color"]
        
        # Note: changing username/email requires password
        
        await client.user.edit(**kwargs)
        return [TextContent(type="text", text="Profile updated")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error editing profile: {str(e)}")]
