"""List and acknowledge Discord pings."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import TextContent

from ..bot import client
from ..tool_utils import NOT_READY_TEXT, apply_rate_limit, format_user_display
from .embed import format_message_body
from .registry import registry


MAX_INBOX_MENTIONS = 100


def _text(value: str) -> list[TextContent]:
    return [TextContent(type="text", text=value)]


def _parse_limit(value: object) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("limit must be an integer") from exc
    if not 1 <= limit <= MAX_INBOX_MENTIONS:
        raise ValueError(f"limit must be between 1 and {MAX_INBOX_MENTIONS}")
    return limit


def _parse_id(value: object, field_name: str) -> int:
    try:
        result = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a Discord ID") from exc
    if result <= 0:
        raise ValueError(f"{field_name} must be a positive Discord ID")
    return result


def _resolve_guild(value: object):
    if value is None or value == "":
        return None
    try:
        guild_id = int(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("guild_id must be a Discord server ID") from exc
    guild = client.get_guild(guild_id)
    if guild is None:
        raise ValueError(f"Server {guild_id} was not found")
    return guild


def _message_row(message) -> dict[str, Any]:
    author = getattr(message, "author", None)
    channel = getattr(message, "channel", None)
    guild = getattr(message, "guild", None) or getattr(channel, "guild", None)
    created_at = getattr(message, "created_at", None)

    return {
        "message_id": str(getattr(message, "id", "")),
        "server": {
            "id": str(getattr(guild, "id", "")) if guild is not None else None,
            "name": getattr(guild, "name", None) if guild is not None else None,
        },
        "channel": {
            "id": str(getattr(channel, "id", "")) if channel is not None else None,
            "name": getattr(channel, "name", None) if channel is not None else None,
        },
        "author": format_user_display(author) if author is not None else "Unknown",
        "created_at": created_at.isoformat() if created_at is not None else None,
        "content": " ".join(format_message_body(message)),
        "jump_url": getattr(message, "jump_url", None),
    }


def _is_unread(message) -> bool:
    """Determine whether a cached Inbox message is newer than the channel ack."""
    channel = getattr(message, "channel", None)
    read_state = getattr(channel, "read_state", None)
    if read_state is None:
        return False
    try:
        return int(message.id) > int(read_state.last_acked_id)
    except (AttributeError, TypeError, ValueError):
        return False


@registry.register(
    name="list_pings",
    description=(
        "List recent Discord pings from the Inbox > Mentions section. By default searches all "
        "servers and includes direct, role, @everyone, and @here mentions. Set both role and "
        "everyone filters false to return only direct mentions."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": MAX_INBOX_MENTIONS},
            "guild_id": {"type": "string", "description": "Optional server ID. Omit to include all servers."},
            "include_role_mentions": {"type": "boolean", "default": True},
            "include_everyone_mentions": {"type": "boolean", "default": True},
            "unread_only": {"type": "boolean", "default": False},
        },
    },
)
async def list_pings(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        limit = _parse_limit(arguments.get("limit", 25))
        guild = _resolve_guild(arguments.get("guild_id"))
        roles = arguments.get("include_role_mentions", True)
        everyone = arguments.get("include_everyone_mentions", True)
        unread_only = arguments.get("unread_only", False)
        if not isinstance(roles, bool):
            raise ValueError("include_role_mentions must be a boolean")
        if not isinstance(everyone, bool):
            raise ValueError("include_everyone_mentions must be a boolean")
        if not isinstance(unread_only, bool):
            raise ValueError("unread_only must be a boolean")

        await apply_rate_limit("action")
        mentions = []
        async for message in client.recent_mentions(limit=limit, guild=guild, roles=roles, everyone=everyone):
            if not unread_only or _is_unread(message):
                mentions.append(_message_row(message))
        if not mentions:
            scope = f"server {guild.name}" if guild is not None else "all servers"
            qualifier = " unread" if unread_only else ""
            return _text(f"No recent{qualifier} inbox mentions found in {scope}.")
        return _text(json.dumps({"mentions": mentions}, indent=2))
    except Exception as exc:
        return _text(f"Error listing pings: {exc}")


@registry.register(
    name="mark_message_read",
    description="Mark messages through one specific message as read, leaving newer messages unread.",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string", "description": "The channel ID returned by list_pings."},
            "message_id": {"type": "string", "description": "The specific message ID to acknowledge."},
        },
        "required": ["channel_id", "message_id"],
    },
)
async def mark_message_read(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        channel_id = _parse_id(arguments.get("channel_id"), "channel_id")
        message_id = _parse_id(arguments.get("message_id"), "message_id")
        channel = client.get_channel(channel_id)
        if channel is None:
            return _text("Channel not found")
        read_state = getattr(channel, "read_state", None)
        if read_state is None or not callable(getattr(read_state, "ack", None)):
            return _text("This channel's read state is unavailable")
        await apply_rate_limit("action")
        await read_state.ack(message_id)
        return _text(f"Marked messages through {message_id} in channel {channel_id} as read.")
    except Exception as exc:
        return _text(f"Error marking message read: {exc}")
