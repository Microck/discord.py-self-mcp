from datetime import datetime, timezone

import pytest
from mcp.types import ImageContent

from discord_py_self_mcp.tools import messages


class FakeAuthor:
    def __init__(self, name="tester", user_id=1):
        self.name = name
        self.id = user_id


class FakeAttachment:
    def __init__(
        self,
        *,
        attachment_id=99,
        filename="photo.png",
        url="https://cdn.discordapp.com/photo.png",
        content_type="image/png",
        size=4,
        width=32,
        height=32,
        description=None,
        payload=b"test",
    ):
        self.id = attachment_id
        self.filename = filename
        self.url = url
        self.content_type = content_type
        self.size = size
        self.width = width
        self.height = height
        self.description = description
        self._payload = payload

    async def read(self):
        return self._payload


class FakeReference:
    def __init__(self, message_id):
        self.message_id = message_id


class FakeMessage:
    def __init__(
        self,
        *,
        message_id=42,
        author=None,
        content="",
        clean_content="",
        attachments=None,
        reference=None,
    ):
        self.id = message_id
        self.author = author or FakeAuthor()
        self.content = content
        self.clean_content = clean_content
        self.attachments = attachments or []
        self.embeds = []
        self.reference = reference
        self.created_at = datetime(2026, 4, 17, 19, 0, tzinfo=timezone.utc)
        self.deleted = False

    async def delete(self):
        self.deleted = True


class FakeHistoryIterator:
    def __init__(self, messages_list):
        self._iter = iter(messages_list)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeMessageable:
    pass


class FakeChannel(FakeMessageable):
    def __init__(self, *, messages_list=None, fetched_message=None, sent_message=None):
        self._messages = messages_list or []
        self._fetched_message = fetched_message
        self._sent_message = sent_message or FakeMessage(message_id=999)
        self.last_history_limit = None
        self.sent_content = None
        self.sent_kwargs = None

    def history(self, **kwargs):
        limit = kwargs.get("limit", len(self._messages))
        self.last_history_limit = limit
        return FakeHistoryIterator(self._messages[:limit])

    async def fetch_message(self, message_id):
        return self._fetched_message

    async def send(self, content, **kwargs):
        self.sent_content = content
        self.sent_kwargs = kwargs
        return self._sent_message


class FakeClient:
    def __init__(self, channel):
        self._channel = channel
        self.user = FakeAuthor(name="self", user_id=777)

    def get_channel(self, channel_id):
        return self._channel


@pytest.mark.asyncio
async def test_send_message_without_reply_has_no_reference(monkeypatch):
    fake_channel = FakeChannel()
    rate_limit_calls = []
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(messages, "apply_rate_limit", fake_apply_rate_limit)

    result = await messages.send_message({"channel_id": "1", "content": "hi"})

    assert rate_limit_calls == ["message"]
    assert fake_channel.sent_content == "hi"
    assert fake_channel.sent_kwargs.get("reference") is None
    assert "message_id=999" in result[0].text


@pytest.mark.asyncio
async def test_send_message_empty_reply_id_sends_normally(monkeypatch):
    fake_channel = FakeChannel()
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    async def fake_apply_rate_limit(action_type):
        pass

    monkeypatch.setattr(messages, "apply_rate_limit", fake_apply_rate_limit)

    result = await messages.send_message(
        {"channel_id": "1", "content": "hi", "reply_to_message_id": ""}
    )

    assert fake_channel.sent_content == "hi"
    assert fake_channel.sent_kwargs.get("reference") is None
    assert "message_id=999" in result[0].text
    assert "Error" not in result[0].text


@pytest.mark.asyncio
async def test_send_message_includes_reply_reference(monkeypatch):
    fake_channel = FakeChannel()
    rate_limit_calls = []
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(messages, "apply_rate_limit", fake_apply_rate_limit)

    result = await messages.send_message(
        {"channel_id": "1", "content": "hi", "reply_to_message_id": "456"}
    )

    assert rate_limit_calls == ["message"]
    reference = fake_channel.sent_kwargs.get("reference")
    assert reference is not None
    assert reference.message_id == 456
    assert reference.channel_id == 1
    assert "message_id=999" in result[0].text


@pytest.mark.asyncio
async def test_read_messages_includes_attachment_metadata(monkeypatch):
    attachment = FakeAttachment()
    fake_message = FakeMessage(message_id=123, attachments=[attachment])
    fake_channel = FakeChannel(messages_list=[fake_message])
    rate_limit_calls = []
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(messages, "apply_rate_limit", fake_apply_rate_limit)

    result = await messages.read_messages({"channel_id": "1", "limit": 5})

    assert "message_id=123" in result[0].text
    assert "[Attachment 0] photo.png" in result[0].text
    assert "url=https://cdn.discordapp.com/photo.png" in result[0].text
    assert rate_limit_calls == ["action"]


@pytest.mark.asyncio
async def test_read_messages_includes_reply_reference_id(monkeypatch):
    reply_msg = FakeMessage(
        message_id=222,
        content="a reply",
        clean_content="a reply",
        reference=FakeReference(message_id=111),
    )
    plain_msg = FakeMessage(
        message_id=333, content="not a reply", clean_content="not a reply"
    )
    fake_channel = FakeChannel(messages_list=[reply_msg, plain_msg])
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    async def fake_apply_rate_limit(action_type):
        pass

    monkeypatch.setattr(messages, "apply_rate_limit", fake_apply_rate_limit)

    result = await messages.read_messages({"channel_id": "1", "limit": 5})
    text = result[0].text

    assert "message_id=222" in text
    assert "reply_to=111" in text
    # A non-reply message should not gain a reply_to marker
    assert "message_id=333" in text
    plain_line = [line for line in text.splitlines() if "message_id=333" in line][0]
    assert "reply_to=" not in plain_line


@pytest.mark.asyncio
async def test_get_message_attachments_returns_image_content(monkeypatch):
    attachment = FakeAttachment(payload=b"png-bytes")
    fake_message = FakeMessage(message_id=456, attachments=[attachment])
    fake_channel = FakeChannel(fetched_message=fake_message)
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    result = await messages.get_message_attachments(
        {"channel_id": "1", "message_id": "456"}
    )

    assert result[0].text.startswith("[Attachment 0] photo.png")
    assert isinstance(result[1], ImageContent)
    assert result[1].mimeType == "image/png"


@pytest.mark.asyncio
async def test_get_message_attachments_can_skip_binary_download(monkeypatch):
    attachment = FakeAttachment()
    fake_message = FakeMessage(message_id=456, attachments=[attachment])
    fake_channel = FakeChannel(fetched_message=fake_message)
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    result = await messages.get_message_attachments(
        {"channel_id": "1", "message_id": "456", "download_content": False}
    )

    assert len(result) == 1
    assert result[0].text.startswith("[Attachment 0] photo.png")


@pytest.mark.asyncio
async def test_delete_message_blocks_other_users(monkeypatch):
    fake_message = FakeMessage(author=FakeAuthor(user_id=123))
    fake_channel = FakeChannel(fetched_message=fake_message)
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    result = await messages.delete_message({"channel_id": "1", "message_id": "456"})

    assert result[0].text == "Cannot delete messages from other users"
    assert fake_message.deleted is False


@pytest.mark.asyncio
async def test_search_messages_applies_rate_limit_and_caps_fetch_window(monkeypatch):
    fake_messages = [
        FakeMessage(message_id=index, content="hello world", clean_content="hello world")
        for index in range(200)
    ]
    fake_channel = FakeChannel(messages_list=fake_messages)
    rate_limit_calls = []
    monkeypatch.setattr(messages.discord.abc, "Messageable", FakeMessageable)
    monkeypatch.setattr(messages, "client", FakeClient(fake_channel))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(messages, "apply_rate_limit", fake_apply_rate_limit)

    result = await messages.search_messages(
        {"channel_id": "1", "query": "hello", "limit": 500}
    )

    assert rate_limit_calls == ["action"]
    assert fake_channel.last_history_limit == 300
    assert "message_id=" in result[0].text
