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

    # Mirrors discord.Role ordering: equal positions are broken by id, and the
    # role with the higher id sorts lower.
    def __lt__(self, other):
        if self.position == other.position:
            return self.id > other.id
        return self.position < other.position

    def __ge__(self, other):
        return not self < other

    async def edit(self, **kwargs):
        # discord.Role.edit returns a new instance and leaves this one untouched.
        self.edits.append(kwargs)
        return FakeRole(
            role_id=self.id,
            name=kwargs.get("name", self.name),
            position=kwargs.get("position", self.position),
        )

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
async def test_edit_role_allows_tie_broken_below_by_id(monkeypatch):
    # Same position as our top role, but a higher id, which Discord orders lower.
    top = FakeRole(role_id=1, name="admin", position=20)
    role = FakeRole(role_id=99, name="tied-below", position=20)
    guild = FakeGuild(roles_list=[role, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    await roles.edit_role({"guild_id": "1", "role_id": "99", "name": "renamed"})

    assert role.edits == [{"name": "renamed"}]


@pytest.mark.asyncio
async def test_edit_role_blocks_tie_broken_above_by_id(monkeypatch):
    # Same position, lower id, which Discord orders above us.
    top = FakeRole(role_id=99, name="mine", position=20)
    role = FakeRole(role_id=1, name="tied-above", position=20)
    guild = FakeGuild(roles_list=[role, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.edit_role({"guild_id": "1", "role_id": "1", "name": "nope"})

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


class FakeGuildBulk(FakeGuild):
    """Guild that exposes the bulk endpoint, like discord.py-self 2.0.1."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bulk_calls = []

    async def edit_role_positions(self, positions, reason=None):
        self.bulk_calls.append((dict(positions), reason))
        # Mirrors the library: fresh Role objects, originals left stale.
        return [
            FakeRole(role_id=role.id, name=role.name, position=position)
            for role, position in positions.items()
        ]


@pytest.mark.asyncio
async def test_reorder_roles_reports_positions_from_the_api_not_stale_cache(monkeypatch):
    first = FakeRole(role_id=10, name="a", position=1)
    second = FakeRole(role_id=11, name="b", position=2)
    top = FakeRole(role_id=1, name="admin", position=100)
    guild = FakeGuildBulk(roles_list=[first, second, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {
            "guild_id": "1",
            "positions": [
                {"role_id": "10", "position": 40},
                {"role_id": "11", "position": 30},
            ],
        }
    )

    text = result[0].text
    assert guild.bulk_calls[0][0] == {first: 40, second: 30}
    # The originals still say 1 and 2; the report must not.
    assert (first.position, second.position) == (1, 2)
    assert "a: asked 40, now 40" in text
    assert "b: asked 30, now 30" in text


@pytest.mark.asyncio
async def test_reorder_roles_reports_positions_after_sequential_fallback(monkeypatch):
    first = FakeRole(role_id=10, name="a", position=1)
    top = FakeRole(role_id=1, name="admin", position=100)
    guild = FakeGuild(roles_list=[first, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {"guild_id": "1", "positions": [{"role_id": "10", "position": 7}]}
    )

    assert first.position == 1
    assert "a: asked 7, now 7" in result[0].text


@pytest.mark.asyncio
async def test_edit_role_blocks_a_destination_above_own_role(monkeypatch):
    role = FakeRole(role_id=10, name="mod", position=5)
    guild = _guild_with(role, my_top_position=20)
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.edit_role({"guild_id": "1", "role_id": "10", "position": 25})

    assert "Position 25 is at or above your highest role" in result[0].text
    assert role.edits == []


@pytest.mark.asyncio
async def test_reorder_roles_blocks_a_destination_above_own_role(monkeypatch):
    first = FakeRole(role_id=10, name="a", position=1)
    top = FakeRole(role_id=1, name="admin", position=20)
    guild = FakeGuild(roles_list=[first, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {"guild_id": "1", "positions": [{"role_id": "10", "position": 30}]}
    )

    assert "a: Position 30 is at or above your highest role" in result[0].text
    assert first.edits == []


@pytest.mark.asyncio
async def test_reorder_roles_names_moves_applied_before_a_failure(monkeypatch):
    class Exploding(FakeRole):
        async def edit(self, **kwargs):
            raise RuntimeError("500 Internal Server Error")

    ok_role = FakeRole(role_id=10, name="a", position=1)
    bad_role = Exploding(role_id=11, name="b", position=2)
    top = FakeRole(role_id=1, name="admin", position=100)
    guild = FakeGuild(roles_list=[ok_role, bad_role, top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {
            "guild_id": "1",
            "positions": [
                {"role_id": "10", "position": 40},
                {"role_id": "11", "position": 30},
            ],
        }
    )

    text = result[0].text
    assert "500 Internal Server Error" in text
    # Highest destination goes first, so "a" is applied before "b" blows up.
    assert "1 role(s) were already moved" in text
    assert "a (10)" in text
    assert "The rest were not touched" in text


@pytest.mark.asyncio
async def test_reorder_roles_reports_missing_role(monkeypatch):
    top = FakeRole(role_id=1, name="admin", position=100)
    guild = FakeGuild(roles_list=[top], me=FakeMe(top))
    monkeypatch.setattr(roles, "client", FakeClient(guild))

    result = await roles.reorder_roles(
        {"guild_id": "1", "positions": [{"role_id": "42", "position": 4}]}
    )

    assert result[0].text == "Role 42 not found"
