import json
from datetime import datetime, timezone

import pytest

from discord_py_self_mcp.tools import inbox


class FakeGuild:
    def __init__(self, guild_id=10, name="Example server"):
        self.id = guild_id
        self.name = name


class FakeReadState:
    def __init__(self, last_acked_id=0):
        self.last_acked_id = last_acked_id
        self.acknowledged = []

    async def ack(self, message_id):
        self.acknowledged.append(message_id)


class FakeChannel:
    def __init__(self, channel_id=20, guild=None, last_acked_id=0):
        self.id = channel_id
        self.name = "general"
        self.guild = guild
        self.read_state = FakeReadState(last_acked_id)


class FakeMessage:
    def __init__(self, message_id, channel):
        self.id = message_id
        self.channel = channel
        self.author = type("Author", (), {"name": "alice", "global_name": None, "discriminator": "0"})()
        self.clean_content = "Hello"
        self.content = "Hello"
        self.embeds = []
        self.attachments = []
        self.created_at = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
        self.jump_url = f"https://discord.com/channels/10/20/{message_id}"


class FakeClient:
    def __init__(self, *, guilds=None, messages=None, channels=None, ready=True):
        self._guilds = {guild.id: guild for guild in guilds or []}
        self._messages = messages or []
        self._channels = {channel.id: channel for channel in channels or []}
        self._ready = ready
        self.calls = []

    def is_ready(self):
        return self._ready

    def get_guild(self, guild_id):
        return self._guilds.get(guild_id)

    def get_channel(self, channel_id):
        return self._channels.get(channel_id)

    def recent_mentions(self, **kwargs):
        self.calls.append(kwargs)

        async def iterate():
            for message in self._messages:
                yield message

        return iterate()


@pytest.mark.asyncio
async def test_list_pings_supports_native_filters_and_unread_filter(monkeypatch):
    guild = FakeGuild()
    read = FakeMessage(40, FakeChannel(guild=guild, last_acked_id=40))
    unread = FakeMessage(41, FakeChannel(guild=guild, last_acked_id=40))
    fake_client = FakeClient(guilds=[guild], messages=[read, unread])
    monkeypatch.setattr(inbox, "client", fake_client)

    async def no_limit(_action_type):
        pass

    monkeypatch.setattr(inbox, "apply_rate_limit", no_limit)
    result = await inbox.list_pings({"include_role_mentions": False, "include_everyone_mentions": False, "unread_only": True})

    assert fake_client.calls == [{"limit": 25, "guild": None, "roles": False, "everyone": False}]
    assert [row["message_id"] for row in json.loads(result[0].text)["mentions"]] == ["41"]


@pytest.mark.asyncio
async def test_mark_message_read_acknowledges_only_through_selected_message(monkeypatch):
    channel = FakeChannel(last_acked_id=30)
    fake_client = FakeClient(channels=[channel])
    monkeypatch.setattr(inbox, "client", fake_client)

    async def no_limit(_action_type):
        pass

    monkeypatch.setattr(inbox, "apply_rate_limit", no_limit)
    result = await inbox.mark_message_read({"channel_id": "20", "message_id": "35"})

    assert channel.read_state.acknowledged == [35]
    assert "through 35" in result[0].text
