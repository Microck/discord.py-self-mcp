import discord
from mcp.types import TextContent

from ..bot import client
from ..tool_utils import format_user_display
from .registry import registry


def _is_group(channel) -> bool:
    return getattr(channel, "type", None) == discord.ChannelType.group


def _recipient_label(user) -> str:
    if user is None:
        return "unknown"
    display = format_user_display(user)
    uid = getattr(user, "id", None)
    bot_tag = " [BOT]" if getattr(user, "bot", False) else ""
    return f"{display} (id={uid}){bot_tag}"


@registry.register(
    name="list_dm_channels",
    description=(
        "List your open direct-message (DM) and group-DM channels with their "
        "channel IDs and recipients. Use this to discover the channel_id needed "
        "by read_messages / send_message instead of having to know it in advance."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "include_groups": {
                "type": "boolean",
                "description": "Include group DMs (default true).",
            },
            "name_contains": {
                "type": "string",
                "description": "Case-insensitive filter: only return DMs whose recipient name/handle contains this.",
            },
        },
    },
)
async def list_dm_channels(arguments: dict):
    try:
        include_groups = arguments.get("include_groups", True)
        name_contains = (arguments.get("name_contains") or "").strip().lower()

        private_channels = list(getattr(client, "private_channels", []) or [])
        if not private_channels:
            return [
                TextContent(
                    type="text",
                    text="No open DM channels are cached. Open a DM in Discord, then try again.",
                )
            ]

        lines = []
        for channel in private_channels:
            is_group = _is_group(channel)
            if is_group and not include_groups:
                continue

            if is_group:
                recipients = list(getattr(channel, "recipients", []) or [])
                name = getattr(channel, "name", None)
                who = "; ".join(_recipient_label(u) for u in recipients) or "(empty group)"
                searchable = " ".join(
                    f"{getattr(u, 'global_name', '') or ''} {getattr(u, 'name', '') or ''}"
                    for u in recipients
                ).lower()
                if name:
                    searchable += " " + name.lower()
                label = f"[group{' ' + repr(name) if name else ''}] {who}"
            else:
                recipient = getattr(channel, "recipient", None)
                who = _recipient_label(recipient)
                searchable = (
                    f"{getattr(recipient, 'global_name', '') or ''} "
                    f"{getattr(recipient, 'name', '') or ''}"
                ).lower()
                label = f"[dm] {who}"

            if name_contains and name_contains not in searchable:
                continue

            lines.append(f"{channel.id} - {label}")

        if not lines:
            scope = "DM channels" if include_groups else "1:1 DM channels"
            extra = f" matching '{name_contains}'" if name_contains else ""
            return [TextContent(type="text", text=f"No {scope}{extra}.")]

        header = f"{len(lines)} DM channel(s):"
        return [TextContent(type="text", text=header + "\n" + "\n".join(lines))]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=f"Error listing DM channels: {type(e).__name__}: {str(e)}",
            )
        ]
