import pytest

from scripts import daemon


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


class FakeMessage:
    def __init__(self, *, message_id=42, attachments=None):
        self.id = message_id
        self.attachments = attachments or []


class FakeMessageable:
    pass


class FakeChannel(FakeMessageable):
    def __init__(self, fetched_message):
        self._fetched_message = fetched_message

    async def fetch_message(self, message_id):
        return self._fetched_message


class FakeClient:
    def __init__(self, channel):
        self._channel = channel

    def get_channel(self, channel_id):
        return self._channel


@pytest.mark.asyncio
async def test_get_message_attachments_returns_metadata_without_download(monkeypatch):
    attachment = FakeAttachment()
    fake_message = FakeMessage(message_id=456, attachments=[attachment])
    daemon_instance = daemon.DiscordDaemon.__new__(daemon.DiscordDaemon)
    daemon_instance.client = FakeClient(FakeChannel(fake_message))

    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    result = await daemon_instance._get_message_attachments(1, 456)

    assert result["message_id"] == 456
    assert result["attachments"][0]["filename"] == "photo.png"
    assert result["attachments"][0]["index"] == 0
    assert "downloads" not in result


@pytest.mark.asyncio
async def test_get_message_attachments_can_inline_download_payloads(monkeypatch):
    attachment = FakeAttachment(payload=b"binary-payload")
    fake_message = FakeMessage(message_id=456, attachments=[attachment])
    daemon_instance = daemon.DiscordDaemon.__new__(daemon.DiscordDaemon)
    daemon_instance.client = FakeClient(FakeChannel(fake_message))

    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    result = await daemon_instance._get_message_attachments(
        1, 456, download_content=True
    )

    assert result["downloads"][0]["filename"] == "photo.png"
    assert result["downloads"][0]["content_type"] == "image/png"
    assert result["downloads"][0]["content_base64"] == "YmluYXJ5LXBheWxvYWQ="
