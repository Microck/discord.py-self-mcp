import base64

import discord
from mcp.types import BlobResourceContents, EmbeddedResource, ImageContent, TextContent

from ..bot import client
from .registry import registry
from .embed import build_search_text, format_attachment, format_message_line
from ..tool_utils import NON_MESSAGEABLE_TEXT, apply_rate_limit, validate_message_content

MAX_ATTACHMENT_BYTES_DEFAULT = 10 * 1024 * 1024


@registry.register(
    name="send_message",
    description="Send a message to a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["channel_id", "content"],
    },
)
async def send_message(arguments: dict):
    """Send a text message to a channel."""
    try:
        channel_id = int(arguments["channel_id"])
        content = arguments["content"]
        content_error = validate_message_content(content)
        if content_error:
            return [TextContent(type="text", text=content_error)]
        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]

        await apply_rate_limit("message")
        message = await channel.send(content)
        return [
            TextContent(
                type="text",
                text=f"Message sent to {channel_id} (message_id={message.id})",
            )
        ]
    except Exception as e:
        return [TextContent(type="text", text=f"Error sending message: {str(e)}")]


@registry.register(
    name="read_messages",
    description="Read messages from a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
        "required": ["channel_id"],
    },
)
async def read_messages(arguments: dict):
    """Read recent messages from a channel."""
    try:
        channel_id = int(arguments["channel_id"])
        limit = arguments.get("limit", 50)
        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]

        messages = []
        async for msg in channel.history(limit=limit):
            messages.append(format_message_line(msg))

        return [TextContent(type="text", text="\n".join(reversed(messages)))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error reading messages: {str(e)}")]


@registry.register(
    name="search_messages",
    description="Search for messages in a channel",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "query": {
                "type": "string",
                "description": "Text to search for (simple containment)",
            },
            "limit": {"type": "integer", "default": 50},
        },
        "required": ["channel_id", "query"],
    },
)
async def search_messages(arguments: dict):
    """Search messages in a guild by keyword with optional filters."""
    try:
        channel_id = int(arguments["channel_id"])
        query = arguments["query"].lower()
        limit = arguments.get("limit", 50)

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]

        messages = []
        # Basic filtering using history since standard search API is not always reliable in selfbots without indexing
        async for msg in channel.history(limit=limit * 2):  # Fetch double to filter
            # Search in content, embeds, and attachment metadata
            search_text = build_search_text(msg)

            if query in search_text:
                messages.append(format_message_line(msg))
                if len(messages) >= limit:
                    break

        if not messages:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"No messages found matching '{arguments['query']}'. "
                        "Try broadening your search or increasing the limit."
                    ),
                )
            ]

        return [TextContent(type="text", text="\n".join(reversed(messages)))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error searching messages: {str(e)}")]


@registry.register(
    name="edit_message",
    description="Edit a message sent by the user",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["channel_id", "message_id", "content"],
    },
)
async def edit_message(arguments: dict):
    """Edit the content of an existing message."""
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        content = arguments["content"]
        content_error = validate_message_content(content)
        if content_error:
            return [TextContent(type="text", text=content_error)]

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]
        message = await channel.fetch_message(message_id)

        if message.author.id != client.user.id:
            return [
                TextContent(type="text", text="Cannot edit messages from other users")
            ]

        await apply_rate_limit("message")
        await message.edit(content=content)
        return [TextContent(type="text", text=f"Edited message {message_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error editing message: {str(e)}")]


@registry.register(
    name="delete_message",
    description="Delete a message",
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
        },
        "required": ["channel_id", "message_id"],
    },
)
async def delete_message(arguments: dict):
    """Delete a message by ID."""
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]
        message = await channel.fetch_message(message_id)

        if message.author.id != client.user.id:
            return [
                TextContent(type="text", text="Cannot delete messages from other users")
            ]

        await apply_rate_limit("action")
        await message.delete()
        return [TextContent(type="text", text=f"Deleted message {message_id}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error deleting message: {str(e)}")]


@registry.register(
    name="get_message_attachments",
    description=(
        "Get attachment metadata for a message and optionally download attachment "
        "content as MCP image/resource outputs"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel_id": {"type": "string"},
            "message_id": {"type": "string"},
            "attachment_index": {
                "type": "integer",
                "description": "Optional zero-based attachment index to fetch",
            },
            "download_content": {
                "type": "boolean",
                "default": True,
                "description": "When false, return only attachment metadata",
            },
            "max_bytes": {
                "type": "integer",
                "default": MAX_ATTACHMENT_BYTES_DEFAULT,
                "description": "Skip downloads above this size",
            },
        },
        "required": ["channel_id", "message_id"],
    },
)
async def get_message_attachments(arguments: dict):
    """Download and return attachments from a message."""
    try:
        channel_id = int(arguments["channel_id"])
        message_id = int(arguments["message_id"])
        attachment_index = arguments.get("attachment_index")
        download_content = arguments.get("download_content", True)
        max_bytes = int(arguments.get("max_bytes", MAX_ATTACHMENT_BYTES_DEFAULT))

        channel = client.get_channel(channel_id)
        if not channel:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                return [TextContent(type="text", text="Channel not found")]
            except discord.Forbidden:
                return [TextContent(type="text", text="Access denied to channel")]

        if not channel:
            return [TextContent(type="text", text="Channel not found")]
        if not isinstance(channel, discord.abc.Messageable):
            return [TextContent(type="text", text=NON_MESSAGEABLE_TEXT)]

        message = await channel.fetch_message(message_id)
        attachments = list(message.attachments)
        if not attachments:
            return [TextContent(type="text", text="Message has no attachments")]

        if attachment_index is not None:
            if attachment_index < 0 or attachment_index >= len(attachments):
                return [
                    TextContent(
                        type="text",
                        text=(
                            f"Attachment index {attachment_index} is out of range for "
                            f"{len(attachments)} attachment(s)"
                        ),
                    )
                ]
            indexed_attachments = [(attachment_index, attachments[attachment_index])]
        else:
            indexed_attachments = list(enumerate(attachments))

        response = [
            TextContent(
                type="text",
                text="\n".join(
                    format_attachment(attachment, index=index)
                    for index, attachment in indexed_attachments
                ),
            )
        ]

        if not download_content:
            return response

        for index, attachment in indexed_attachments:
            if attachment.size is not None and attachment.size > max_bytes:
                response.append(
                    TextContent(
                        type="text",
                        text=(
                            f"Skipped attachment {index} ({attachment.filename}) because "
                            f"size={attachment.size} exceeds max_bytes={max_bytes}"
                        ),
                    )
                )
                continue

            blob = await attachment.read()
            encoded = base64.b64encode(blob).decode("ascii")
            mime_type = attachment.content_type or "application/octet-stream"

            if mime_type.startswith("image/"):
                response.append(
                    ImageContent(type="image", data=encoded, mimeType=mime_type)
                )
            else:
                response.append(
                    EmbeddedResource(
                        type="resource",
                        resource=BlobResourceContents(
                            uri=attachment.url,
                            mimeType=mime_type,
                            blob=encoded,
                        ),
                    )
                )

        return response
    except discord.NotFound:
        return [TextContent(type="text", text="Message not found")]
    except discord.Forbidden:
        return [TextContent(type="text", text="Access denied to message")]
    except Exception as e:
        return [
            TextContent(type="text", text=f"Error getting message attachments: {str(e)}")
        ]
