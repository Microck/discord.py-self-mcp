from mcp.types import TextContent

from ..bot import client
from .registry import registry


@registry.register(
    name="create_invite",
    description="Create an invite for a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "max_age": {
                "type": "integer",
                "description": "Duration in seconds (0 = never expire)",
            },
            "max_uses": {"type": "integer", "description": "Max uses (0 = unlimited)"},
            "temporary": {"type": "boolean", "description": "Temporary membership"},
        },
        "required": ["channel_id"],
    },
)
async def create_invite(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        max_age = arguments.get("max_age", 86400)  # 24h default
        max_uses = arguments.get("max_uses", 0)
        temporary = arguments.get("temporary", False)

        channel = client.get_channel(channel_id) or await client.fetch_channel(
            channel_id
        )

        invite = await channel.create_invite(
            max_age=max_age,
            max_uses=max_uses,
            temporary=temporary,
            validate=True,
        )
        return [TextContent(type="text", text=f"Created invite: {invite.url}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating invite: {str(e)}")]


@registry.register(
    name="list_invites",
    description="List invites for a guild",
    input_schema={
        "type": "object",
        "properties": {"guild_id": {"type": "string"}},
        "required": ["guild_id"],
    },
)
async def list_invites(arguments: dict):
    try:
        guild_id = int(arguments["guild_id"])
        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        invites = await guild.invites()
        invite_list = [f"{i.code} (Uses: {i.uses})" for i in invites]

        if not invite_list:
            return [TextContent(type="text", text="No invites found")]

        return [TextContent(type="text", text="\n".join(invite_list))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing invites: {str(e)}")]


@registry.register(
    name="delete_invite",
    description="Delete an invite",
    input_schema={
        "type": "object",
        "properties": {"invite_code": {"type": "string"}},
        "required": ["invite_code"],
    },
)
async def delete_invite(arguments: dict):
    try:
        invite_code = arguments["invite_code"]
        # Need to fetch invite object to delete it? Or use guild.
        # discord.py Invite object has delete()
        # We can try to fetch it first

        invite = await client.fetch_invite(invite_code)
        await invite.delete()
        return [TextContent(type="text", text=f"Deleted invite {invite_code}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting invite: {str(e)}")]
