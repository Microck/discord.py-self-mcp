import pytest

from discord_py_self_mcp.tools import relationships


class FakeUser:
    def __init__(self, id, name, global_name=None, discriminator="0"):
        self.id = id
        self.name = name
        self.global_name = global_name
        self.discriminator = discriminator


class FakeRelationship:
    """Mirrors discord.Relationship: exposes .user (and .id) but no .name."""

    def __init__(self, user):
        self.user = user

    @property
    def id(self):
        return self.user.id


class FakeClient:
    def __init__(self, friends):
        self.friends = friends


@pytest.mark.asyncio
async def test_list_friends_formats_relationship_users(monkeypatch):
    friends = [
        FakeRelationship(FakeUser(1, "alice", global_name="Alice")),
        FakeRelationship(FakeUser(2, "bob")),
    ]
    monkeypatch.setattr(relationships, "client", FakeClient(friends))

    result = await relationships.list_friends({})

    # A Relationship has no .name, so it must be formatted via its .user.
    assert result[0].text == "Alice (@alice) (1)\nbob (2)"


@pytest.mark.asyncio
async def test_list_friends_empty(monkeypatch):
    monkeypatch.setattr(relationships, "client", FakeClient([]))

    result = await relationships.list_friends({})

    assert result[0].text == "Your friends list is empty."


@pytest.mark.asyncio
async def test_list_friends_skips_relationship_without_user(monkeypatch):
    friends = [
        FakeRelationship(FakeUser(1, "alice", global_name="Alice")),
        FakeRelationship(None),
    ]
    monkeypatch.setattr(relationships, "client", FakeClient(friends))

    result = await relationships.list_friends({})

    assert result[0].text == "Alice (@alice) (1)"
