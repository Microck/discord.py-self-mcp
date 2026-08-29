import json

import discord
import pytest

from discord_py_self_mcp.tools import dms


class FakeUser:
    def __init__(self, uid, name, global_name=None, discriminator="0", bot=False):
        self.id = uid
        self.name = name
        self.global_name = global_name
        self.discriminator = discriminator
        self.bot = bot


class FakeDM:
    type = discord.ChannelType.private

    def __init__(self, channel_id, recipient):
        self.id = channel_id
        self.recipient = recipient
        self.last_message_id = None
        self.read_state = None


class FakeGroup:
    type = discord.ChannelType.group

    def __init__(self, channel_id, recipients, name=None):
        self.id = channel_id
        self.recipients = recipients
        self.name = name
        self.last_message_id = None
        self.read_state = None


class FakeReadState:
    def __init__(self, last_acked_id, badge_count=0):
        self.last_acked_id = last_acked_id
        self.badge_count = badge_count


class FakeClient:
    def __init__(self, private_channels):
        self.private_channels = private_channels

    def is_ready(self):
        return True


@pytest.mark.asyncio
async def test_empty(monkeypatch):
    monkeypatch.setattr(dms, "client", FakeClient([]))
    result = await dms.list_dm_channels({})
    assert "No open DM channels are cached" in result[0].text


@pytest.mark.asyncio
async def test_lists_dm_and_group(monkeypatch):
    carol = FakeUser(1001, "carol")
    alice = FakeUser(2001, "alice")
    bob = FakeUser(2002, "bob")
    channels = [
        FakeDM(500, carol),
        FakeGroup(600, [alice, bob], name="planning"),
    ]
    monkeypatch.setattr(dms, "client", FakeClient(channels))

    result = await dms.list_dm_channels({})
    text = result[0].text
    assert "2 DM channel(s):" in text
    assert "500 - [dm] carol (id=1001)" in text
    assert "600 - [group 'planning']" in text
    assert "alice (id=2001)" in text and "bob (id=2002)" in text


@pytest.mark.asyncio
async def test_exclude_groups(monkeypatch):
    carol = FakeUser(1001, "carol")
    alice = FakeUser(2001, "alice")
    channels = [FakeDM(500, carol), FakeGroup(600, [alice])]
    monkeypatch.setattr(dms, "client", FakeClient(channels))

    result = await dms.list_dm_channels({"include_groups": False})
    text = result[0].text
    assert "1 DM channel(s):" in text
    assert "500 - [dm]" in text
    assert "600" not in text


@pytest.mark.asyncio
async def test_name_filter(monkeypatch):
    carol = FakeUser(1001, "carol")
    dave = FakeUser(1002, "dave")
    channels = [FakeDM(500, carol), FakeDM(501, dave)]
    monkeypatch.setattr(dms, "client", FakeClient(channels))

    result = await dms.list_dm_channels({"name_contains": "carol"})
    text = result[0].text
    assert "1 DM channel(s):" in text
    assert "500 - [dm] carol" in text
    assert "501" not in text


@pytest.mark.asyncio
async def test_bot_tag(monkeypatch):
    helper = FakeUser(555000111222333444, "helperbot", bot=True)
    channels = [FakeDM(700, helper)]
    monkeypatch.setattr(dms, "client", FakeClient(channels))

    result = await dms.list_dm_channels({})
    text = result[0].text
    assert "[BOT]" in text
    assert "helperbot" in text


@pytest.mark.asyncio
async def test_global_name_display(monkeypatch):
    user = FakeUser(1003, "nightowl", global_name="Owl")
    channels = [FakeDM(800, user)]
    monkeypatch.setattr(dms, "client", FakeClient(channels))

    result = await dms.list_dm_channels({})
    # format_user_display -> "Owl (@nightowl)"
    assert "Owl (@nightowl)" in result[0].text


@pytest.mark.asyncio
async def test_list_unread_dms_returns_unread_direct_and_group_dms(monkeypatch):
    carol = FakeUser(1001, "carol")
    alice = FakeUser(2001, "alice")
    unread_dm = FakeDM(500, carol)
    unread_dm.last_message_id = 120
    unread_dm.read_state = FakeReadState(100, badge_count=1)
    read_dm = FakeDM(501, carol)
    read_dm.last_message_id = 100
    read_dm.read_state = FakeReadState(100)
    unread_group = FakeGroup(600, [alice], name="planning")
    unread_group.last_message_id = 220
    unread_group.read_state = FakeReadState(200)
    monkeypatch.setattr(dms, "client", FakeClient([unread_dm, read_dm, unread_group]))

    result = await dms.list_unread_dms({})

    payload = json.loads(result[0].text)
    assert [row["channel_id"] for row in payload["unread_dms"]] == ["500", "600"]
    assert payload["unread_dms"][0]["mention_count"] == 1


@pytest.mark.asyncio
async def test_list_unread_dms_respects_limit_and_rejects_booleans(monkeypatch):
    carol = FakeUser(1001, "carol")
    first = FakeDM(500, carol)
    first.last_message_id = 120
    first.read_state = FakeReadState(100)
    second = FakeDM(501, carol)
    second.last_message_id = 120
    second.read_state = FakeReadState(100)
    monkeypatch.setattr(dms, "client", FakeClient([first, second]))

    result = await dms.list_unread_dms({"limit": 1})
    assert [row["channel_id"] for row in json.loads(result[0].text)["unread_dms"]] == ["500"]

    invalid = await dms.list_unread_dms({"limit": True})
    assert "limit must be an integer" in invalid[0].text
