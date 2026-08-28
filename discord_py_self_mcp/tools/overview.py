"""High-signal, low-volume guild discovery tools."""

import json
import re
from collections import Counter
from typing import Any

from mcp.types import TextContent

from ..bot import client
from ..logging_utils import log_to_stderr
from ..tool_utils import NOT_READY_TEXT, apply_rate_limit, format_user_display
from .folders import _get_settings, _serialize_folders
from .registry import registry


DEFAULT_OVERVIEW_FIELDS = ("description", "channels", "member_count", "permissions", "folder")
MAX_GUILDS_PER_REQUEST = 100
MAX_MESSAGES_PER_GUILD = 30
MAX_SAMPLE_CHANNELS = 4
_PREFERRED_CHANNEL_WORDS = (
    "announcement",
    "update",
    "news",
    "welcome",
    "start-here",
    "about",
    "faq",
    "rules",
    "general",
    "community",
    "help",
)
_NOISY_CHANNEL_PATTERN = re.compile(
    r"(?:^|[-_ ])(ticket|transcript|log|join|leave|ban|mod-log|bot-commands?|counting)(?:$|[-_ ])|^ticket[-_ ]?\d+",
    re.IGNORECASE,
)
_NUMBERED_CHANNEL_PATTERN = re.compile(r"\d+")


def _text(value: str) -> list[TextContent]:
    return [TextContent(type="text", text=value)]


def _channel_type(channel) -> str:
    value = getattr(channel, "type", None)
    return str(getattr(value, "name", value or "unknown")).lower()


def _channel_category_name(channel) -> str | None:
    category = getattr(channel, "category", None)
    name = getattr(category, "name", None)
    return str(name) if name else None


def _is_messageable(channel) -> bool:
    return callable(getattr(channel, "history", None))


def _is_noisy_channel(channel) -> bool:
    return bool(_NOISY_CHANNEL_PATTERN.search(str(getattr(channel, "name", ""))))


def _channel_priority(channel) -> tuple[int, str]:
    name = str(getattr(channel, "name", "")).lower()
    preferred_index = next(
        (index for index, word in enumerate(_PREFERRED_CHANNEL_WORDS) if word in name),
        len(_PREFERRED_CHANNEL_WORDS),
    )
    return (preferred_index, name)


def _channel_row(channel) -> dict[str, Any]:
    return {
        "id": str(getattr(channel, "id", "")),
        "name": str(getattr(channel, "name", "")),
        "type": _channel_type(channel),
        "category": _channel_category_name(channel),
    }


def _channel_summary(guild, *, include_repetitive: bool = False) -> dict[str, Any]:
    channels = list(getattr(guild, "channels", ()) or ())
    counts = Counter(_channel_type(channel) for channel in channels)
    categories = sorted(
        {
            category
            for category in (_channel_category_name(channel) for channel in channels)
            if category
        }
    )
    messageable = [channel for channel in channels if _is_messageable(channel) and not _is_noisy_channel(channel)]
    notable = [_channel_row(channel) for channel in sorted(messageable, key=_channel_priority)[:20]]

    repetitive: dict[str, list[str]] = {}
    for channel in channels:
        name = str(getattr(channel, "name", ""))
        normalized = _NUMBERED_CHANNEL_PATTERN.sub("*", name)
        if normalized != name:
            repetitive.setdefault(normalized, []).append(name)
    repetitive_rows = [
        {"pattern": pattern, "count": len(names)}
        for pattern, names in sorted(repetitive.items())
        if len(names) >= 3
    ]

    summary: dict[str, Any] = {
        "categories": categories,
        "notable_channels": notable,
        "counts": dict(sorted(counts.items())),
    }
    if include_repetitive:
        summary["channels"] = [_channel_row(channel) for channel in channels]
    else:
        summary["repetitive_channels"] = repetitive_rows
    return summary


def _resolve_guilds(arguments: dict) -> list:
    raw_guild_ids = arguments.get("guild_ids")
    if raw_guild_ids is None:
        guilds = list(client.guilds)
        if len(guilds) > MAX_GUILDS_PER_REQUEST:
            raise ValueError(
                f"This account has more than {MAX_GUILDS_PER_REQUEST} servers; provide guild_ids in batches"
            )
        return guilds
    if not isinstance(raw_guild_ids, list) or not raw_guild_ids:
        raise ValueError("guild_ids must be a non-empty array of server IDs")
    if len(raw_guild_ids) > MAX_GUILDS_PER_REQUEST:
        raise ValueError(f"guild_ids may contain at most {MAX_GUILDS_PER_REQUEST} server IDs")

    guilds = []
    missing = []
    for value in raw_guild_ids:
        try:
            guild_id = int(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("guild_ids must contain Discord server IDs") from exc
        guild = client.get_guild(guild_id)
        if guild is None:
            missing.append(str(guild_id))
        else:
            guilds.append(guild)
    if missing:
        raise ValueError(f"Server(s) not found: {', '.join(missing)}")
    return guilds


def _guild_permissions(guild) -> dict[str, bool]:
    me = getattr(guild, "me", None)
    permissions = getattr(me, "guild_permissions", None)
    user = getattr(client, "user", None)
    return {
        "owner": getattr(guild, "owner_id", None) == getattr(user, "id", None),
        "administrator": bool(getattr(permissions, "administrator", False)),
        "manage_guild": bool(getattr(permissions, "manage_guild", False)),
        "manage_channels": bool(getattr(permissions, "manage_channels", False)),
        "manage_messages": bool(getattr(permissions, "manage_messages", False)),
    }


def _folder_index(settings) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for folder in _serialize_folders(settings):
        for guild_id in folder["guild_ids"]:
            result[guild_id] = {
                "id": folder["folder_id"],
                "name": folder["name"],
                "color": folder["color"],
            }
    return result


def _sample_message(channel, message) -> dict[str, Any]:
    content = str(getattr(message, "clean_content", None) or getattr(message, "content", "")).strip()
    if len(content) > 500:
        content = content[:497] + "..."
    author = getattr(message, "author", None)
    created_at = getattr(message, "created_at", None)
    return {
        "channel_id": str(getattr(channel, "id", "")),
        "channel_name": str(getattr(channel, "name", "")),
        "message_id": str(getattr(message, "id", "")),
        "author": format_user_display(author) if author else None,
        "created_at": created_at.isoformat() if created_at else None,
        "content": content,
    }


async def _sample_guild(guild, messages_per_guild: int, sample_channels: int) -> list[dict[str, Any]]:
    channels = [
        channel
        for channel in getattr(guild, "channels", ()) or ()
        if _is_messageable(channel) and not _is_noisy_channel(channel)
    ]
    selected = sorted(channels, key=_channel_priority)[:sample_channels]
    if not selected:
        return []

    per_channel = max(1, (messages_per_guild + len(selected) - 1) // len(selected))
    samples: list[dict[str, Any]] = []
    for channel in selected:
        try:
            await apply_rate_limit("action")
            async for message in channel.history(limit=per_channel):
                samples.append(_sample_message(channel, message))
                if len(samples) >= messages_per_guild:
                    return samples
        except Exception as exc:
            log_to_stderr(
                f"[OVERVIEW] Skipped history for guild={guild.id} channel={getattr(channel, 'id', 'unknown')}: {exc}"
            )
    return samples


async def _build_overviews(arguments: dict, *, force_samples: bool = False) -> dict[str, Any]:
    guilds = _resolve_guilds(arguments)
    requested = arguments.get("include", list(DEFAULT_OVERVIEW_FIELDS))
    if not isinstance(requested, list) or any(not isinstance(item, str) for item in requested):
        raise ValueError("include must be an array of field names")
    include = set(requested)
    include_samples = force_samples or arguments.get("include_recent_messages", False) or "recent_messages" in include
    messages_per_guild = int(arguments.get("recent_messages_per_server", 10))
    sample_channels = int(arguments.get("sample_channels_per_server", 3))
    if not 1 <= messages_per_guild <= MAX_MESSAGES_PER_GUILD:
        raise ValueError(f"recent_messages_per_server must be between 1 and {MAX_MESSAGES_PER_GUILD}")
    if not 1 <= sample_channels <= MAX_SAMPLE_CHANNELS:
        raise ValueError(f"sample_channels_per_server must be between 1 and {MAX_SAMPLE_CHANNELS}")

    folder_by_guild: dict[str, dict[str, Any]] = {}
    all_folders: list[dict[str, Any]] = []
    if "folder" in include:
        settings = await _get_settings()
        all_folders = _serialize_folders(settings)
        folder_by_guild = _folder_index(settings)

    log_to_stderr(
        f"[OVERVIEW] Building overview for {len(guilds)} server(s); samples={include_samples}"
    )
    servers = []
    for guild in guilds:
        row: dict[str, Any] = {"guild_id": str(guild.id), "name": guild.name}
        if "description" in include:
            row["description"] = getattr(guild, "description", None)
        if "channels" in include:
            row["channel_summary"] = _channel_summary(
                guild, include_repetitive=arguments.get("include_repetitive_channels", False)
            )
        if "member_count" in include:
            row["member_count"] = getattr(guild, "member_count", None)
        if "permissions" in include:
            row["permissions"] = _guild_permissions(guild)
        if "folder" in include:
            row["folder"] = folder_by_guild.get(str(guild.id))
        if include_samples:
            row["recent_message_samples"] = await _sample_guild(
                guild, messages_per_guild, sample_channels
            )
        servers.append(row)

    payload: dict[str, Any] = {"servers": servers}
    if "folder" in include:
        payload["folders"] = all_folders
    return payload


@registry.register(
    name="get_server_overviews",
    description="Get compact, multi-server metadata and channel summaries in one call.",
    input_schema={
        "type": "object",
        "properties": {
            "guild_ids": {"type": "array", "items": {"type": "string"}},
            "include": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["description", "channels", "member_count", "permissions", "folder", "recent_messages"],
                },
                "description": "Defaults to description, channels, member_count, permissions, and folder",
            },
            "recent_messages_per_server": {"type": "integer", "default": 10},
            "sample_channels_per_server": {"type": "integer", "default": 3},
            "include_repetitive_channels": {"type": "boolean", "default": False},
        },
    },
)
async def get_server_overviews(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        return _text(json.dumps(await _build_overviews(arguments), indent=2))
    except Exception as exc:
        return _text(f"Error getting server overviews: {exc}")


@registry.register(
    name="sample_server_content",
    description="Sample recent messages from high-signal channels across multiple servers, skipping likely logs and ticket channels.",
    input_schema={
        "type": "object",
        "properties": {
            "guild_ids": {"type": "array", "items": {"type": "string"}},
            "messages_per_guild": {"type": "integer", "default": 10},
            "sample_channels_per_guild": {"type": "integer", "default": 3},
        },
        "required": ["guild_ids"],
    },
)
async def sample_server_content(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    mapped = dict(arguments)
    mapped["recent_messages_per_server"] = mapped.pop("messages_per_guild", 10)
    mapped["sample_channels_per_server"] = mapped.pop("sample_channels_per_guild", 3)
    mapped["include"] = ["recent_messages"]
    try:
        payload = await _build_overviews(mapped, force_samples=True)
        return _text(json.dumps(payload, indent=2))
    except Exception as exc:
        return _text(f"Error sampling server content: {exc}")


@registry.register(
    name="analyze_server_sidebar",
    description="Return the full sidebar classification view: current folders, compact channel summaries, permissions, and optional representative messages.",
    input_schema={
        "type": "object",
        "properties": {
            "guild_ids": {"type": "array", "items": {"type": "string"}},
            "include_recent_messages": {"type": "boolean", "default": False},
            "recent_messages_per_server": {"type": "integer", "default": 10},
            "sample_channels_per_server": {"type": "integer", "default": 3},
            "include_repetitive_channels": {"type": "boolean", "default": False},
        },
    },
)
async def analyze_server_sidebar(arguments: dict):
    if not client.is_ready():
        return _text(NOT_READY_TEXT)
    try:
        return _text(json.dumps(await _build_overviews(arguments), indent=2))
    except Exception as exc:
        return _text(f"Error analyzing server sidebar: {exc}")
