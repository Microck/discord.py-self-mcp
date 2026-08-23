import asyncio

import discord
import pytest

from discord_py_self_mcp import modal_store
from discord_py_self_mcp.tools import interactions


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    """The limiter is enabled by default and spaces actions 12s apart."""

    async def noop(action_type):
        return None

    monkeypatch.setattr(interactions, "apply_rate_limit", noop)


# --- Fakes -------------------------------------------------------------------


class FakeUser:
    def __init__(self, uid, name="bot", bot=True):
        self.id = uid
        self.name = name
        self.bot = bot


class FakeOption:
    def __init__(self, name):
        self.name = name


class FakeSlashCommand:
    """Stand-in for discord.SlashCommand. Constructable from (state, data,
    channel) like the real class, callable like a command."""

    def __init__(self, *, state=None, data=None, channel=None):
        data = data or {}
        self.name = data.get("name")
        self.options = [FakeOption(o["name"]) for o in data.get("options", [])]
        self.children = [
            FakeSubCommand(c["name"]) for c in data.get("children", [])
        ]
        self.application_id = data.get("application_id")
        self.channel = channel
        self.called_with = None

    def is_group(self):
        return bool(self.children)

    async def __call__(self, channel, **opts):
        self.called_with = (channel, opts)
        return type("Interaction", (), {"id": 12345})()


class FakeSubCommand:
    def __init__(self, name, children=None, options=None):
        self.name = name
        self.children = children or []
        self.options = options or []
        self.called_with = None

    def is_group(self):
        return bool(self.children)

    async def __call__(self, channel, **opts):
        self.called_with = (channel, opts)
        return type("Interaction", (), {"id": 67890})()


class FakeChannel(discord.abc.Messageable):
    def __init__(self, channel_id=1, recipient=None, search=None):
        self.id = channel_id
        self.recipient = recipient
        self._search = search or []

    async def _get_channel(self):
        return self

    def slash_commands(self, query=None, **kw):
        results = self._search

        async def gen():
            for c in results:
                yield c

        return gen()


class FakeHTTP:
    def __init__(self, commands=None, error=None):
        self._commands = commands if commands is not None else []
        self._error = error

    async def get_application_commands(self, app_id):
        if self._error:
            raise self._error
        return self._commands


class FakeClient:
    def __init__(self, channel=None, commands=None, http_error=None, no_channel=False):
        self._channel = channel
        self.http = FakeHTTP(commands=commands, error=http_error)
        self._connection = object()
        self._no_channel = no_channel

    def get_channel(self, channel_id):
        return None if self._no_channel else self._channel

    async def fetch_channel(self, channel_id):
        if self._no_channel:
            raise discord.NotFound  # type: ignore[call-arg]
        return self._channel


# --- _infer_application_id ----------------------------------------------------


def test_infer_application_id_explicit_wins():
    ch = FakeChannel(recipient=FakeUser(99, bot=True))
    assert interactions._infer_application_id(ch, "555") == "555"


def test_infer_application_id_bot_dm():
    ch = FakeChannel(recipient=FakeUser(777, bot=True))
    assert interactions._infer_application_id(ch, None) == "777"


def test_infer_application_id_non_bot_dm_is_none():
    ch = FakeChannel(recipient=FakeUser(777, bot=False))
    assert interactions._infer_application_id(ch, None) is None


def test_infer_application_id_no_recipient_is_none():
    ch = FakeChannel(recipient=None)
    assert interactions._infer_application_id(ch, None) is None


# --- send_slash_command -------------------------------------------------------


@pytest.mark.asyncio
async def test_options_must_be_object(monkeypatch):
    monkeypatch.setattr(interactions, "client", FakeClient())
    result = await interactions.send_slash_command(
        {"channel_id": "1", "command_name": "x", "options": "not-a-dict"}
    )
    assert result[0].text == "options must be an object"


@pytest.mark.asyncio
async def test_channel_not_found(monkeypatch):
    monkeypatch.setattr(interactions, "client", FakeClient(no_channel=True))
    result = await interactions.send_slash_command(
        {"channel_id": "1", "command_name": "x"}
    )
    assert result[0].text == "Channel not found"


@pytest.mark.asyncio
async def test_executes_via_application_listing(monkeypatch):
    channel = FakeChannel(channel_id=10)
    commands = [
        {"name": "help", "id": "1", "version": "2", "type": 1, "application_id": "123", "options": []}
    ]
    monkeypatch.setattr(interactions, "client", FakeClient(channel=channel, commands=commands))
    monkeypatch.setattr(discord, "SlashCommand", FakeSlashCommand)

    result = await interactions.send_slash_command(
        {"channel_id": "10", "command_name": "help", "application_id": "123"}
    )
    assert result[0].text.startswith("Executed slash command: /help")
    assert "interaction 12345" in result[0].text


@pytest.mark.asyncio
async def test_infers_app_id_in_bot_dm(monkeypatch):
    channel = FakeChannel(channel_id=20, recipient=FakeUser(123, bot=True))
    commands = [
        {"name": "stats", "id": "1", "version": "2", "type": 1, "application_id": "123", "options": []}
    ]
    monkeypatch.setattr(interactions, "client", FakeClient(channel=channel, commands=commands))
    monkeypatch.setattr(discord, "SlashCommand", FakeSlashCommand)

    result = await interactions.send_slash_command(
        {"channel_id": "20", "command_name": "stats"}
    )
    assert result[0].text.startswith("Executed slash command: /stats")


@pytest.mark.asyncio
async def test_not_found_lists_available_commands(monkeypatch):
    channel = FakeChannel(channel_id=10)
    commands = [
        {"name": "help", "id": "1", "version": "2", "type": 1, "application_id": "123", "options": []},
        {"name": "stats", "id": "2", "version": "2", "type": 1, "application_id": "123", "options": []},
    ]
    monkeypatch.setattr(interactions, "client", FakeClient(channel=channel, commands=commands))
    monkeypatch.setattr(discord, "SlashCommand", FakeSlashCommand)

    result = await interactions.send_slash_command(
        {"channel_id": "10", "command_name": "nope", "application_id": "123"}
    )
    text = result[0].text
    assert "not found" in text
    assert "/help" in text and "/stats" in text


@pytest.mark.asyncio
async def test_unknown_option_is_reported(monkeypatch):
    channel = FakeChannel(channel_id=10)
    commands = [
        {"name": "greet", "id": "1", "version": "2", "type": 1, "application_id": "123",
         "options": [{"name": "text", "type": 3}]}
    ]
    monkeypatch.setattr(interactions, "client", FakeClient(channel=channel, commands=commands))
    monkeypatch.setattr(discord, "SlashCommand", FakeSlashCommand)

    result = await interactions.send_slash_command(
        {"channel_id": "10", "command_name": "greet", "application_id": "123",
         "options": {"bogus": "x"}}
    )
    text = result[0].text
    assert text.startswith("Executed slash command: /greet")
    assert "Ignored unknown option(s)" in text and "bogus" in text


@pytest.mark.asyncio
async def test_group_without_subcommand_is_rejected(monkeypatch):
    channel = FakeChannel(channel_id=10)
    commands = [
        {"name": "config", "id": "1", "version": "2", "type": 1, "application_id": "123",
         "children": [{"name": "set"}, {"name": "get"}]}
    ]
    monkeypatch.setattr(interactions, "client", FakeClient(channel=channel, commands=commands))
    monkeypatch.setattr(discord, "SlashCommand", FakeSlashCommand)

    result = await interactions.send_slash_command(
        {"channel_id": "10", "command_name": "config", "application_id": "123"}
    )
    text = result[0].text
    assert "command group" in text
    assert "set" in text and "get" in text


@pytest.mark.asyncio
async def test_http_error_is_surfaced_not_masked(monkeypatch):
    channel = FakeChannel(channel_id=10)
    monkeypatch.setattr(
        interactions,
        "client",
        FakeClient(channel=channel, http_error=RuntimeError("boom")),
    )
    # No fallback possible: app id is explicit, listing failed, search has nothing.
    result = await interactions.send_slash_command(
        {"channel_id": "10", "command_name": "x", "application_id": "123"}
    )
    text = result[0].text
    # app listing failed -> search fallback runs -> nothing found -> not found,
    # and the original RuntimeError is appended so it is not silently masked.
    assert "not found" in text
    assert "boom" in text


@pytest.mark.asyncio
async def test_falls_back_to_search_without_app_id(monkeypatch):
    fake_cmd = FakeSlashCommand(data={"name": "foo", "options": []})
    channel = FakeChannel(channel_id=30, recipient=None, search=[fake_cmd])
    monkeypatch.setattr(interactions, "client", FakeClient(channel=channel))
    monkeypatch.setattr(discord, "SlashCommand", FakeSlashCommand)

    result = await interactions.send_slash_command(
        {"channel_id": "30", "command_name": "foo"}
    )
    assert result[0].text.startswith("Executed slash command: /foo")
    assert fake_cmd.called_with is not None


# --- Button / modal fakes ----------------------------------------------------


class FakeTextInput:
    def __init__(self, custom_id, label=None, required=True,
                 min_length=None, max_length=None):
        self.custom_id = custom_id
        self.label = label
        self.required = required
        self.min_length = min_length
        self.max_length = max_length
        self.value = None

    def answer(self, value, /):
        self.value = value


class FakeActionRow:
    def __init__(self, *children):
        self.children = list(children)


class FakeModal:
    def __init__(self, custom_id="auth_profile:ABC", title="프로필", components=None):
        self.custom_id = custom_id
        self.title = title
        self.components = components or []
        self.submitted = False

    async def submit(self):
        self.submitted = True


class FakeButton(discord.Button):
    """Must subclass the real Button: click_button gates on isinstance.

    discord.Button uses __slots__ and sets __repr_info__ = __slots__, so an
    unset slot blows up repr() when an assertion fails. Every slot is filled
    here. The subclass itself declares no __slots__, so it still gets a
    __dict__ for the test-only attributes.
    """

    def __init__(self, custom_id, label=None, disabled=False, click_result=None):
        self.message = None
        self.style = None
        self.custom_id = custom_id
        self.url = None
        self.disabled = disabled
        self.label = label
        self.emoji = None
        self._click_result = click_result
        self.clicked = False

    async def click(self):
        self.clicked = True
        return self._click_result


class FakeMessageChannel(discord.abc.Messageable):
    def __init__(self, channel_id=1, message=None):
        self.id = channel_id
        self._message = message

    async def _get_channel(self):
        return self

    async def fetch_message(self, message_id):
        return self._message


class FakeMessage:
    def __init__(self, *rows):
        self.components = list(rows)


class FakeModalClient:
    """Client stub whose wait_for either yields a modal or times out."""

    def __init__(self, channel=None, modal=None):
        self._channel = channel
        self._modal = modal

    def get_channel(self, channel_id):
        return self._channel

    async def wait_for(self, event, timeout=None):
        assert event == "modal"
        if self._modal is None:
            raise asyncio.TimeoutError
        return self._modal


# --- click_button ------------------------------------------------------------


@pytest.mark.asyncio
async def test_click_button_without_modal_keeps_legacy_message(monkeypatch):
    button = FakeButton("auth_panel")
    channel = FakeMessageChannel(message=FakeMessage(FakeActionRow(button)))
    monkeypatch.setattr(interactions, "client", FakeModalClient(channel=channel))

    result = await interactions.click_button(
        {"channel_id": "1", "message_id": "2", "custom_id": "auth_panel"}
    )

    assert button.clicked
    assert result[0].text == "Button clicked"


@pytest.mark.asyncio
async def test_click_button_reports_modal_fields(monkeypatch):
    modal = FakeModal(
        custom_id="auth_profile:ABC",
        components=[FakeActionRow(
            FakeTextInput("profile_username", label="유저네임",
                          required=True, min_length=3, max_length=20)
        )],
    )
    button = FakeButton("auth_panel")
    channel = FakeMessageChannel(message=FakeMessage(FakeActionRow(button)))
    monkeypatch.setattr(
        interactions, "client", FakeModalClient(channel=channel, modal=modal)
    )

    result = await interactions.click_button(
        {"channel_id": "1", "message_id": "2", "custom_id": "auth_panel"}
    )

    text = result[0].text
    assert "auth_profile:ABC" in text
    assert "profile_username" in text
    assert "유저네임" in text


@pytest.mark.asyncio
async def test_click_button_url_button_is_unchanged(monkeypatch):
    button = FakeButton("link", click_result="https://example.com")
    channel = FakeMessageChannel(message=FakeMessage(FakeActionRow(button)))
    monkeypatch.setattr(interactions, "client", FakeModalClient(channel=channel))

    result = await interactions.click_button(
        {"channel_id": "1", "message_id": "2", "custom_id": "link"}
    )

    assert result[0].text == "Button is a URL: https://example.com"


# --- submit_modal ------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_modal_store():
    modal_store.clear()
    yield
    modal_store.clear()


def _stash(modal):
    modal_store.put(modal)
    return modal


@pytest.mark.asyncio
async def test_submit_modal_answers_and_submits():
    field = FakeTextInput("profile_username", required=True)
    modal = _stash(FakeModal(components=[FakeActionRow(field)]))

    result = await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC",
         "values": {"profile_username": "erickong1108"}}
    )

    assert field.value == "erickong1108"
    assert modal.submitted
    assert "submitted" in result[0].text.lower()


@pytest.mark.asyncio
async def test_submit_modal_consumes_the_entry():
    modal = _stash(FakeModal(components=[
        FakeActionRow(FakeTextInput("profile_username", required=False))
    ]))
    await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC", "values": {}}
    )
    assert modal_store.take("auth_profile:ABC") is None


@pytest.mark.asyncio
async def test_submit_modal_unknown_id_explains():
    _stash(FakeModal(custom_id="other"))

    result = await interactions.submit_modal(
        {"custom_id": "auth_profile:GONE", "values": {}}
    )

    text = result[0].text
    assert "auth_profile:GONE" in text
    assert "other" in text


@pytest.mark.asyncio
async def test_submit_modal_missing_required_field_is_rejected():
    field = FakeTextInput("profile_username", required=True)
    modal = _stash(FakeModal(components=[FakeActionRow(field)]))

    result = await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC", "values": {}}
    )

    assert "profile_username" in result[0].text
    assert not modal.submitted


@pytest.mark.asyncio
async def test_submit_modal_missing_required_field_keeps_the_modal():
    _stash(FakeModal(components=[
        FakeActionRow(FakeTextInput("profile_username", required=True))
    ]))
    await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC", "values": {}}
    )
    assert modal_store.take("auth_profile:ABC") is not None


@pytest.mark.asyncio
async def test_submit_modal_reports_unknown_keys():
    field = FakeTextInput("profile_username", required=True)
    _stash(FakeModal(components=[FakeActionRow(field)]))

    result = await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC",
         "values": {"profile_username": "ok", "typo_field": "x"}}
    )

    assert "typo_field" in result[0].text
    assert field.value == "ok"


@pytest.mark.asyncio
async def test_submit_modal_length_violation_is_reported():
    class StrictInput(FakeTextInput):
        def answer(self, value, /):
            raise ValueError("value must be at least 3 characters long")

    modal = _stash(FakeModal(components=[
        FakeActionRow(StrictInput("profile_username", required=True))
    ]))

    result = await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC", "values": {"profile_username": "a"}}
    )

    assert "at least 3 characters" in result[0].text
    assert not modal.submitted


@pytest.mark.asyncio
async def test_submit_modal_values_must_be_an_object():
    _stash(FakeModal())
    result = await interactions.submit_modal(
        {"custom_id": "auth_profile:ABC", "values": "nope"}
    )
    assert "values must be an object" in result[0].text
