import pytest

from discord_py_self_mcp.tools import threads


class FakeForumThread:
    def __init__(self, thread_id=321, name="Forum Thread"):
        self.id = thread_id
        self.name = name


class FakeForumThreadResult:
    def __init__(self, thread=None):
        self.thread = thread or FakeForumThread()


class FakeForumChannel:
    def __init__(self):
        self.calls = []

    async def create_thread(self, **kwargs):
        self.calls.append(kwargs)
        return FakeForumThreadResult()


class FakeClient:
    def __init__(self, channel):
        self._channel = channel

    def get_channel(self, channel_id):
        return self._channel


@pytest.mark.asyncio
async def test_create_thread_supports_forum_content(monkeypatch):
    channel = FakeForumChannel()
    rate_limit_calls = []
    monkeypatch.setattr(threads.discord, "ForumChannel", FakeForumChannel)
    monkeypatch.setattr(threads, "client", FakeClient(channel))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(threads, "apply_rate_limit", fake_apply_rate_limit)

    result = await threads.create_thread(
        {"channel_id": "1", "name": "Release thread", "content": "Initial post"}
    )

    assert rate_limit_calls == ["action"]
    assert channel.calls == [{"name": "Release thread", "content": "Initial post"}]
    assert result[0].text == "Created thread Forum Thread (321)"


@pytest.fixture(autouse=True)
def _allow_uploads(tmp_path, monkeypatch):
    root = tmp_path / "uploads"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("UPLOAD_DIRS", str(root))
    return root


class FakeThread:
    def __init__(self, thread_id=321):
        self.id = thread_id
        self.sent_content = None
        self.sent_kwargs = None

    async def send(self, content, **kwargs):
        self.sent_content = content
        self.sent_kwargs = kwargs
        return type("Sent", (), {"id": 999})()


@pytest.mark.asyncio
async def test_send_thread_message_attaches_files(monkeypatch, _allow_uploads):
    thread = FakeThread()
    rate_limit_calls = []
    monkeypatch.setattr(threads.discord, "Thread", FakeThread)
    monkeypatch.setattr(threads, "client", FakeClient(thread))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(threads, "apply_rate_limit", fake_apply_rate_limit)

    upload = _allow_uploads / "notes.txt"
    upload.write_bytes(b"hi")

    result = await threads.send_thread_message(
        {"thread_id": "321", "content": "attached", "file_paths": [str(upload)]}
    )

    assert rate_limit_calls == ["message"]
    assert thread.sent_content == "attached"
    assert [f.filename for f in thread.sent_kwargs["files"]] == ["notes.txt"]
    assert "message_id=999" in result[0].text
    assert "with 1 attachment: notes.txt" in result[0].text


@pytest.mark.asyncio
async def test_send_thread_message_without_files_omits_files_kwarg(monkeypatch):
    thread = FakeThread()
    monkeypatch.setattr(threads.discord, "Thread", FakeThread)
    monkeypatch.setattr(threads, "client", FakeClient(thread))

    async def fake_apply_rate_limit(action_type):
        return None

    monkeypatch.setattr(threads, "apply_rate_limit", fake_apply_rate_limit)

    await threads.send_thread_message({"thread_id": "321", "content": "plain"})

    assert "files" not in thread.sent_kwargs


@pytest.mark.asyncio
async def test_send_thread_message_rejects_missing_file_without_sending(
    monkeypatch, _allow_uploads
):
    thread = FakeThread()
    rate_limit_calls = []
    monkeypatch.setattr(threads.discord, "Thread", FakeThread)
    monkeypatch.setattr(threads, "client", FakeClient(thread))

    async def fake_apply_rate_limit(action_type):
        rate_limit_calls.append(action_type)

    monkeypatch.setattr(threads, "apply_rate_limit", fake_apply_rate_limit)

    missing = str(_allow_uploads / "absent.txt")
    result = await threads.send_thread_message(
        {"thread_id": "321", "content": "oops", "file_paths": [missing]}
    )

    assert result[0].text == f"File not found: {missing}"
    assert thread.sent_content is None
    assert rate_limit_calls == []
