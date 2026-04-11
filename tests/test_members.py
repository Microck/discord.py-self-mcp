import pytest

from discord_py_self_mcp.tools import members


class FakeClient:
    def __init__(self, guild):
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild


class FakeMember:
    def __init__(self, name="test-user"):
        self.name = name
        self.removed_roles = []

    async def remove_roles(self, role):
        self.removed_roles.append(role)


class FakeRole:
    def __init__(self, name="mod"):
        self.name = name


class FakeGuild:
    def __init__(self, member=None, fetched_member=None, role=None):
        self._member = member
        self._fetched_member = fetched_member
        self._role = role

    def get_member(self, user_id):
        return self._member

    async def fetch_member(self, user_id):
        return self._fetched_member

    def get_role(self, role_id):
        return self._role


@pytest.mark.asyncio
async def test_add_role_returns_guild_not_found(monkeypatch):
    monkeypatch.setattr(members, "client", FakeClient(None))

    result = await members.add_role(
        {"guild_id": "1", "user_id": "2", "role_id": "3"}
    )

    assert result[0].text == "Guild not found"


@pytest.mark.asyncio
async def test_add_role_returns_member_not_found(monkeypatch):
    guild = FakeGuild(member=None, fetched_member=None, role=FakeRole())
    monkeypatch.setattr(members, "client", FakeClient(guild))

    result = await members.add_role(
        {"guild_id": "1", "user_id": "2", "role_id": "3"}
    )

    assert result[0].text == "Member not found"


@pytest.mark.asyncio
async def test_remove_role_returns_guild_not_found(monkeypatch):
    monkeypatch.setattr(members, "client", FakeClient(None))

    result = await members.remove_role(
        {"guild_id": "1", "user_id": "2", "role_id": "3"}
    )

    assert result[0].text == "Guild not found"


@pytest.mark.asyncio
async def test_remove_role_removes_role(monkeypatch):
    member = FakeMember()
    role = FakeRole()
    guild = FakeGuild(member=member, fetched_member=None, role=role)
    monkeypatch.setattr(members, "client", FakeClient(guild))

    result = await members.remove_role(
        {"guild_id": "1", "user_id": "2", "role_id": "3"}
    )

    assert result[0].text == "Removed role mod from test-user"
    assert member.removed_roles == [role]
