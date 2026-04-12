from mcp.types import TextContent

from ..bot import client
from .registry import registry


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
