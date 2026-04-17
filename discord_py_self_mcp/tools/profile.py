import discord
from mcp.types import TextContent

from ..bot import client
from ..tool_utils import apply_rate_limit
from .registry import registry

@registry.register(
    name="edit_profile",
    description="Edit user profile fields supported by this server (bio and accent color)",
    input_schema={
        "type": "object",
        "properties": {
            "bio": {"type": "string"},
            "accent_color": {"type": "integer", "description": "Integer color value"},
        }
    }
)
async def edit_profile(arguments: dict):
    try:
        kwargs = {}
        if "bio" in arguments:
            kwargs["bio"] = arguments["bio"]
        if "accent_color" in arguments:
            kwargs["accent_colour"] = arguments["accent_color"]

        await apply_rate_limit("action")
        await client.user.edit(**kwargs)
        return [TextContent(type="text", text="Profile updated")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error editing profile: {str(e)}")]
