from mcp.types import TextContent

from ..bot import client
from ..tool_utils import apply_rate_limit
from .overview import _channel_row, _channel_summary
from .registry import registry

@registry.register(
    name="create_channel",
    description="Create a new channel in a guild",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string"},
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["text", "voice"], "default": "text"},
            "category_id": {"type": "string", "description": "Optional category ID"}
        },
        "required": ["guild_id", "name"]
    }
)
async def create_channel(arguments: dict):
    try:
        guild_id = int(arguments["guild_id"])
        name = arguments["name"]
        channel_type = arguments.get("type", "text")
        category_id = arguments.get("category_id")

        guild = client.get_guild(guild_id)
        if not guild:
            return [TextContent(type="text", text="Guild not found")]

        category = None
        if category_id:
            category = guild.get_channel(int(category_id))

        if channel_type == "text":
            await apply_rate_limit("action")
            channel = await guild.create_text_channel(name, category=category)
        elif channel_type == "voice":
            await apply_rate_limit("action")
            channel = await guild.create_voice_channel(name, category=category)
        else:
            return [TextContent(type="text", text="Invalid channel type")]

        return [TextContent(type="text", text=f"Created channel {channel.name} ({channel.id})")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error creating channel: {str(e)}")]

@registry.register(
    name="delete_channel",
    description="Delete a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"}
        },
        "required": ["channel_id"]
    }
)
async def delete_channel(arguments: dict):
    try:
        channel_id = int(arguments["channel_id"])
        channel = client.get_channel(channel_id)
        if not channel:
             return [TextContent(type="text", text="Channel not found")]

        await apply_rate_limit("action")
        await channel.delete()
        return [TextContent(type="text", text=f"Deleted channel {channel.name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting channel: {str(e)}")]

@registry.register(
    name="list_channels",
    description="List channels for one or more guilds. Summary mode returns compact categories, counts, and notable channels.",
    input_schema={
        "type": "object",
        "properties": {
            "guild_id": {"type": "string", "description": "Single server ID (legacy form)"},
            "guild_ids": {"type": "array", "items": {"type": "string"}, "description": "Multiple server IDs"},
            "mode": {"type": "string", "enum": ["full", "summary"], "default": "full"},
            "include_repetitive": {
                "type": "boolean",
                "default": False,
                "description": "In summary mode, include every repetitive channel instead of collapsed patterns",
            },
        },
        "anyOf": [{"required": ["guild_id"]}, {"required": ["guild_ids"]}],
    },
)
async def list_channels(arguments: dict):
    try:
        raw_guild_ids = arguments.get("guild_ids")
        legacy_single = raw_guild_ids is None
        if legacy_single:
            raw_guild_ids = [arguments.get("guild_id")]
        if not isinstance(raw_guild_ids, list) or not raw_guild_ids:
            return [TextContent(type="text", text="guild_id or guild_ids is required")]
        if len(raw_guild_ids) > 100:
            return [TextContent(type="text", text="guild_ids may contain at most 100 server IDs")]

        guilds = []
        missing = []
        for raw_guild_id in raw_guild_ids:
            guild_id = int(str(raw_guild_id))
            guild = client.get_guild(guild_id)
            if guild is None:
                missing.append(str(guild_id))
            else:
                guilds.append(guild)
        if missing:
            return [TextContent(type="text", text=f"Guild(s) not found: {', '.join(missing)}")]

        mode = arguments.get("mode", "full")
        if mode not in {"full", "summary"}:
            return [TextContent(type="text", text="mode must be full or summary")]
        if legacy_single and mode == "full":
            # Preserve the original text response for existing callers.
            channels = [
                f"{channel.name} ({channel.id}) - {channel.type.name}"
                for channel in guilds[0].channels
            ]
            return [TextContent(type="text", text="\n".join(channels))]

        payload = {"guilds": []}
        for guild in guilds:
            row = {"guild_id": str(guild.id), "guild_name": guild.name}
            if mode == "summary":
                row["channel_summary"] = _channel_summary(
                    guild, include_repetitive=arguments.get("include_repetitive", False)
                )
            else:
                row["channels"] = [_channel_row(channel) for channel in guild.channels]
            payload["guilds"].append(row)
        import json

        return [TextContent(type="text", text=json.dumps(payload, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error listing channels: {str(e)}")]
