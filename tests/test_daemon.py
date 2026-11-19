import asyncio
import json

import pytest

from scripts import daemon


@pytest.mark.asyncio
async def test_reads_fragmented_upload_requests():
    reader = asyncio.StreamReader()
    request = {"command": "send_message_with_files", "args": {"file_paths": ["/" + "📄" * 8000]}}
    data = json.dumps(request).encode()
    reader.feed_data(data[:20])
    pending = asyncio.create_task(daemon.read_command(reader))
    await asyncio.sleep(0)
    reader.feed_data(data[20:])
    reader.feed_eof()
    assert await pending == request


@pytest.mark.asyncio
async def test_rejects_requests_over_the_byte_limit(monkeypatch):
    monkeypatch.setattr(daemon, "MAX_REQUEST_BYTES", 100)
    reader = asyncio.StreamReader()
    reader.feed_data(json.dumps({"content": "x" * 100}).encode())
    reader.feed_eof()
    with pytest.raises(ValueError, match="size limit"):
        await daemon.read_command(reader)


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


@pytest.fixture(autouse=True)
def _allow_uploads(tmp_path, monkeypatch):
    """Uploads are refused unless UPLOAD_DIRS names a directory."""
    root = tmp_path / "uploads"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("UPLOAD_DIRS", str(root))
    return root


def write_upload(root, name="notes.txt", content=b"hi"):
    path = root / name
    path.write_bytes(content)
    return str(path)


class FakeSendChannel(FakeMessageable):
    def __init__(self):
        self.sent_content = "unset"
        self.sent_kwargs = None
        self.sent_message = None

    async def send(self, content, **kwargs):
        self.sent_content = content
        self.sent_kwargs = kwargs
        # Discord renames colliding uploads, so the receipt deliberately differs
        # from what was handed in: reporting the input handles would hide that
        uploaded = kwargs.get("files") or []
        self.sent_message = FakeMessage(
            message_id=999,
            attachments=[
                FakeAttachment(
                    attachment_id=index, filename=f"discord-side-{f.filename}"
                )
                for index, f in enumerate(uploaded)
            ],
        )
        return self.sent_message


def make_daemon(channel):
    daemon_instance = daemon.DiscordDaemon.__new__(daemon.DiscordDaemon)
    daemon_instance.client = FakeClient(channel)
    return daemon_instance


@pytest.mark.asyncio
async def test_daemon_attachment_send_reports_receipt_from_the_message(
    monkeypatch, _allow_uploads
):
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)
    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    upload = write_upload(_allow_uploads, "budget.xlsx")
    result = await daemon_instance._send_message(1, "the files", file_paths=[upload])

    assert result["success"] is True
    assert channel.sent_content == "the files"
    assert [f.filename for f in channel.sent_kwargs["files"]] == ["budget.xlsx"]
    # the receipt reports what Discord says landed (it renames collisions), not
    # the names we handed it
    assert result["attachments"] == ["discord-side-budget.xlsx"]


@pytest.mark.asyncio
async def test_daemon_attachment_send_blank_caption(monkeypatch, _allow_uploads):
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)
    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    upload = write_upload(_allow_uploads, "photo.png", b"png")
    result = await daemon_instance._send_message(1, "", file_paths=[upload])

    assert result["success"] is True
    assert channel.sent_content is None


@pytest.mark.asyncio
async def test_daemon_attachment_send_rejects_missing_file(
    monkeypatch, _allow_uploads
):
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)
    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    missing = str(_allow_uploads / "gone.txt")
    result = await daemon_instance._send_message(1, "hi", file_paths=[missing])

    assert result == {"error": f"File not found: {missing}"}
    assert channel.sent_content == "unset"


@pytest.mark.asyncio
async def test_daemon_plain_send_message_is_unchanged(monkeypatch):
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)
    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    result = await daemon_instance._send_message(1, "plain text")

    assert result == {"message_id": 999, "success": True}
    assert "files" not in channel.sent_kwargs


@pytest.mark.asyncio
async def test_daemon_plain_send_message_refuses_file_paths(
    monkeypatch, _allow_uploads
):
    # posting the caption and quietly dropping the files would look like success
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)
    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    upload = write_upload(_allow_uploads)
    result = await daemon_instance.handle_command(
        {
            "command": "send_message",
            "args": {"channel_id": 1, "content": "x", "file_paths": [upload]},
        }
    )

    assert "send_message_with_files" in result["error"]
    assert channel.sent_content == "unset"


@pytest.mark.asyncio
async def test_daemon_routes_attachment_command_with_files(monkeypatch, _allow_uploads):
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)
    monkeypatch.setattr(daemon.discord.abc, "Messageable", FakeMessageable)

    upload = write_upload(_allow_uploads, "notes.txt")
    result = await daemon_instance.handle_command(
        {
            "command": "send_message_with_files",
            "args": {"channel_id": 1, "content": "x", "file_paths": [upload]},
        }
    )

    assert result["success"] is True
    assert [f.filename for f in channel.sent_kwargs["files"]] == ["notes.txt"]


@pytest.mark.asyncio
async def test_daemon_attachment_command_requires_files(monkeypatch):
    channel = FakeSendChannel()
    daemon_instance = make_daemon(channel)

    result = await daemon_instance.handle_command(
        {"command": "send_message_with_files", "args": {"channel_id": 1, "content": "x"}}
    )

    assert "file_paths" in result["error"]
    assert channel.sent_content == "unset"


@pytest.mark.asyncio
async def test_daemon_rejects_unknown_command():
    daemon_instance = daemon.DiscordDaemon.__new__(daemon.DiscordDaemon)

    result = await daemon_instance.handle_command(
        {"command": "not_a_command", "args": {}}
    )

    assert "error" in result
