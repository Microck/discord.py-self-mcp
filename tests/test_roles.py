import json

import discord
import pytest

from discord_py_self_mcp.tools import roles


class FakeClient:
    def __init__(self, guild):
        self._guild = guild

    def get_guild(self, guild_id):
        return self._guild


class FakeRole:
    def __init__(self, role_id=10, name="mod", position=5):
        self.id = role_id
        self.name = name
        self.position = position
        self.color = discord.Color(0x5865F2)
        self.hoist = False
        self.mentionable = False
        self.managed = False
        self.permissions = discord.Permissions(0)
        self.edits = []
        self.deleted = False

    async def edit(self, **kwargs):
        self.edits.append(kwargs)

    async def delete(self, **kwargs):
        self.deleted = True


class FakeMe:
    def __init__(self, top_role):
        self.id = 999
        self.top_role = top_role


class FakeGuild:
    def __init__(self, roles_list=None, me=None, owner_id=None):
        self.roles = roles_list or []
        self.me = me
        self.owner_id = owner_id
        self.created = []

    def get_role(self, role_id):
        for role in self.roles:
            if role.id == role_id:
                return role
        return None

    async def create_role(self, **kwargs):
        role = FakeRole(role_id=77, name=kwargs.get("name", "new"), position=1)
        self.created.append(kwargs)
        return role


def _guild_with(role, my_top_position=100):
    top = FakeRole(role_id=1, name="admin", position=my_top_position)
    return FakeGuild(roles_list=[role, top], me=FakeMe(top))


@pytest.mark.asyncio
async def test_list_roles_returns_guild_not_found(monkeypatch):
    monkeypatch.setattr(roles, "client", FakeClient(None))

    result = await roles.list_roles({"guild_id": "1"})

    assert result[0].text == "Guild not found"


@pytest.mark.asyncio
async def test_list_roles_sorts_highest_first(monkeypatch):
    low = FakeRole(role_id=10, name="member", position=1)
    high = FakeRole(role_id=11, name="admin", position=9)
    monkeypatch.setattr(roles, "client", FakeClient(FakeGuild(roles_list=[low, high])))

    result = await roles.list_roles({"guild_id": "1"})
    payload = json.loads(result[0].text)

    assert [entry["name"] for entry in payload] == ["admin", "member"]
    assert payload[0]["color"] == "#5865F2"


@pytest.mark.asyncio
async def test_create_role_parses_hex_color(monkeypatch):
    guild = FakeGuild()
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.create_role(
        {"guild_id": "1", "name": "staff", "color": "#FF0000", "hoist": True}
    )

    assert "Created role staff" in result[0].text
    assert guild.created[0]["color"] == discord.Color(0xFF0000)
    assert guild.created[0]["hoist"] is True


@pytest.mark.asyncio
async def test_create_role_accepts_permission_names(monkeypatch):
    guild = FakeGuild()
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    await roles.create_role(
        {"guild_id": "1", "name": "staff", "permissions": ["kick_members"]}
    )

    assert guild.created[0]["permissions"].kick_members is True
    assert guild.created[0]["permissions"].ban_members is False


@pytest.mark.asyncio
async def test_create_role_rejects_unknown_permission_name(monkeypatch):
    monkeypatch.setattr(roles, "client", FakeClient(FakeGuild()))

    result = await roles.create_role(
        {"guild_id": "1", "name": "staff", "permissions": ["make_coffee"]}
    )

    assert "Unknown permission name(s): make_coffee" in result[0].text


@pytest.mark.asyncio
async def test_edit_role_without_fields_changes_nothing(monkeypatch):
    role = FakeRole()
    monkeypatch.setattr(roles, "client", FakeClient(_guild_with(role)))

    result = await roles.edit_role({"guild_id": "1", "role_id": "10"})

    assert result[0].text == "Nothing to change — pass at least one field"
    assert role.edits == []


@pytest.mark.asyncio
async def test_edit_role_applies_only_given_fields(monkeypatch):
    role = FakeRole()
    monkeypatch.setattr(roles, "client", FakeClient(_guild_with(role)))

    result = await roles.edit_role(
        {"guild_id": "1", "role_id": "10", "name": "staff", "hoist": True}
    )

    assert role.edits == [{"name": "staff", "hoist": True}]
    assert "Edited role mod" in result[0].text


@pytest.mark.asyncio
async def test_edit_role_blocks_role_above_own(monkeypatch):
    role = FakeRole(role_id=10, name="owner-only", position=50)
    monkeypatch.setattr(roles, "client", FakeClient(_guild_with(role, my_top_position=20)))

    result = await roles.edit_role({"guild_id": "1", "role_id": "10", "name": "nope"})

    assert "at or above your highest role" in result[0].text
    assert role.edits == []


@pytest.mark.asyncio
async def test_edit_role_allows_guild_owner_above_own_role(monkeypatch):
    role = FakeRole(role_id=10, name="top", position=50)
    top = FakeRole(role_id=1, name="mine", position=2)
    me = FakeMe(top)
    guild = FakeGuild(roles_list=[role, top], me=me, owner_id=me.id)
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    await roles.edit_role({"guild_id": "1", "role_id": "10", "name": "renamed"})

    assert role.edits == [{"name": "renamed"}]


@pytest.mark.asyncio
async def test_delete_role_reports_name(monkeypatch):
    role = FakeRole()
    monkeypatch.setattr(roles, "client", FakeClient(_guild_with(role)))

    result = await roles.delete_role({"guild_id": "1", "role_id": "10"})

    assert result[0].text == "Deleted role mod"
    assert role.deleted is True


@pytest.mark.asyncio
async def test_reorder_roles_falls_back_to_sequential_edits(monkeypatch):
    first = FakeRole(role_id=10, name="a", position=1)
    second = FakeRole(role_id=11, name="b", position=2)
    top = FakeRole(role_id=1, name="admin", position=100)
    guild = FakeGuild(roles_list=[first, second, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {
            "guild_id": "1",
            "positions": [
                {"role_id": "10", "position": 4},
                {"role_id": "11", "position": 3},
            ],
        }
    )

    assert first.edits == [{"position": 4}]
    assert second.edits == [{"position": 3}]
    assert "Reordered 2 role(s)" in result[0].text


@pytest.mark.asyncio
async def test_reorder_roles_reports_missing_role(monkeypatch):
    top = FakeRole(role_id=1, name="admin", position=100)
    guild = FakeGuild(roles_list=[top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {"guild_id": "1", "positions": [{"role_id": "42", "position": 4}]}
    )

    assert result[0].text == "Role 42 not found"
