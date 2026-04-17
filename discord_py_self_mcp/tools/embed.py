import discord


def get_message_text(message: discord.Message) -> str:
    """Prefer clean content when available so mentions are readable."""
    clean_content = getattr(message, "clean_content", None)
    if clean_content:
        return clean_content
    return message.content or ""


def format_embed(embed: discord.Embed) -> str:
    """Format a Discord embed into readable text."""
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


def format_attachment(attachment: discord.Attachment, index: int | None = None) -> str:
    parts = []
    parts.append(f"[Attachment {index}]" if index is not None else "[Attachment]")
    parts.append(attachment.filename)

    if attachment.content_type:
        parts.append(f"type={attachment.content_type}")
    if attachment.size is not None:
        parts.append(f"size={attachment.size}")
    if getattr(attachment, "width", None) and getattr(attachment, "height", None):
        parts.append(f"dimensions={attachment.width}x{attachment.height}")

    parts.append(f"url={attachment.url}")
    return " ".join(parts)


def format_message_body(message: discord.Message) -> list[str]:
    parts = []
    content = get_message_text(message)
    if content:
        parts.append(content)

    for embed in message.embeds:
        embed_text = format_embed(embed)
        if embed_text:
            parts.append(f"[Embed]: {embed_text}")

    for index, attachment in enumerate(message.attachments):
        parts.append(format_attachment(attachment, index=index))

    if not parts:
        parts.append("[No content]")

    return parts


def format_message_line(message: discord.Message) -> str:
    author_name = message.author.name if message.author else "Unknown"
    return f"{author_name} (message_id={message.id}): " + " ".join(
        format_message_body(message)
    )


def build_search_text(message: discord.Message) -> str:
    searchable_parts = [get_message_text(message).lower()]

    for embed in message.embeds:
        embed_text = format_embed(embed)
        if embed_text:
            searchable_parts.append(embed_text.lower())

    for attachment in message.attachments:
        searchable_parts.append(attachment.filename.lower())
        if attachment.content_type:
            searchable_parts.append(attachment.content_type.lower())
        if getattr(attachment, "description", None):
            searchable_parts.append(attachment.description.lower())
        searchable_parts.append(attachment.url.lower())

    return " ".join(part for part in searchable_parts if part)


def serialize_attachment(attachment: discord.Attachment) -> dict:
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "url": attachment.url,
        "content_type": attachment.content_type,
        "size": attachment.size,
        "width": getattr(attachment, "width", None),
        "height": getattr(attachment, "height", None),
        "description": getattr(attachment, "description", None),
    }


def serialize_message(message: discord.Message) -> dict:
    return {
        "id": message.id,
        "author": message.author.name if message.author else "Unknown",
        "content": get_message_text(message),
        "created_at": message.created_at.isoformat(),
        "attachments": [
            serialize_attachment(attachment) for attachment in message.attachments
        ],
    }
