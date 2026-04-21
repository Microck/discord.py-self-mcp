import discord

from .bot import rate_limiter

DISCORD_MESSAGE_LIMIT = 2000
NOT_READY_TEXT = "Discord connection is not ready yet. Please try again in a few seconds."
NON_MESSAGEABLE_TEXT = (
    "Cannot send messages to this channel. It may not support text messages."
)


async def apply_rate_limit(action_type: str) -> None:
    """Apply rate limiting before performing an action, if enabled."""
    if rate_limiter and rate_limiter.is_enabled():
        await rate_limiter.wait_if_needed(action_type)


def format_user_display(user: discord.abc.User) -> str:
    """Format a Discord user for display with global name, username, or discriminator."""
    global_name = getattr(user, "global_name", None)
    if global_name:
        return f"{global_name} (@{user.name})"

    discriminator = getattr(user, "discriminator", None)
    if discriminator and discriminator != "0":
        return f"{user.name}#{discriminator}"

    return user.name


def validate_message_content(content: str) -> str | None:
    """Validate message content length against Discord's 2000-char limit."""
    if len(content) > DISCORD_MESSAGE_LIMIT:
        return (
            f"Message content exceeds Discord's {DISCORD_MESSAGE_LIMIT} character limit"
        )
    return None
