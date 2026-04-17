import discord


def format_embed(embed: discord.Embed) -> str:
    """Format a Discord embed into readable text.

    Extracts the title, author, description, fields, thumbnail URL,
    image URL, and footer from the embed and concatenates them with
    labeled prefixes.

    Args:
        embed: The Discord embed object to format.

    Returns:
        str: A newline-separated string of labeled embed fields, or an
            empty string if the input is not a :class:`discord.Embed`.
    """
    if not isinstance(embed, discord.Embed):
        return ""

    parts = []

    if embed.title:
        parts.append(f"[Title]: {embed.title}")

    if embed.author and embed.author.name:
        parts.append(f"[Author]: {embed.author.name}")

    if embed.description:
        parts.append(f"[Description]: {embed.description}")

    if embed.fields:
        for field in embed.fields:
            parts.append(f"[Field: {field.name}]: {field.value}")

    if embed.thumbnail and embed.thumbnail.url:
        parts.append(f"[Thumbnail]: {embed.thumbnail.url}")

    if embed.image and embed.image.url:
        parts.append(f"[Image]: {embed.image.url}")

    if embed.footer and embed.footer.text:
        parts.append(f"[Footer]: {embed.footer.text}")

    return "\n".join(parts)
