import discord

from .bot import rate_limiter

DISCORD_MESSAGE_LIMIT = 2000
DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 200
NOT_READY_TEXT = "Discord connection is not ready yet. Please try again in a few seconds."
NON_MESSAGEABLE_TEXT = (
    "Cannot send messages to this channel. It may not support text messages."
)


async def apply_rate_limit(action_type: str) -> None:
    if rate_limiter and rate_limiter.is_enabled():
        await rate_limiter.wait_if_needed(action_type)


def format_user_display(user: discord.abc.User) -> str:
    global_name = getattr(user, "global_name", None)
    if global_name:
        return f"{global_name} (@{user.name})"

    discriminator = getattr(user, "discriminator", None)
    if discriminator and discriminator != "0":
        return f"{user.name}#{discriminator}"

    return user.name


def validate_message_content(content: str) -> str | None:
    if len(content) > DISCORD_MESSAGE_LIMIT:
        return (
            f"Message content exceeds Discord's {DISCORD_MESSAGE_LIMIT} character limit"
        )
    return None


def build_reply_kwargs(reply_to_message_id: object, channel_id: object) -> dict:
    """Build channel.send() kwargs for an optional reply reference.

    Returns an empty dict when no reply target is given (None or empty
    string), so the message is sent normally. Otherwise returns a
    ``reference`` pointing at the target message in the given channel.
    """
    if not reply_to_message_id:
        return {}
    return {
        "reference": discord.MessageReference(
            message_id=int(reply_to_message_id),
            channel_id=int(channel_id),
        )
    }


def normalize_history_limit(limit: object, *, default: int = DEFAULT_HISTORY_LIMIT) -> int:
    try:
        normalized = int(limit)
    except (TypeError, ValueError):
        normalized = default

    return max(1, min(normalized, MAX_HISTORY_LIMIT))
