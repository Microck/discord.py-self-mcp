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
