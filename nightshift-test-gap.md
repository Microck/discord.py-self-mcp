# Test Coverage Gap Analysis — discord.py-self-mcp

**Repository:** Microck/discord.py-self-mcp  
**Date:** 2026-04-06  
**Analyzed by:** Nightshift Agent  

---

## Summary

This is a Discord selfbot MCP server with **25 Python files** across 4 packages. The codebase implements an MCP (Model Context Protocol) server that exposes Discord selfbot capabilities as tools, plus a CLI daemon for direct Discord interaction.

**Overall test coverage: 0%** — No test files, test directories, or test configuration exist anywhere in the repository.

| Metric | Value |
|---|---|
| Python source files | 25 |
| Test files | **0** |
| Public tool handlers | ~30 |
| Estimated testable functions | ~45 |
| Test coverage | **0%** |

---

## Current Test Status

### Files Found
- **No `test_*.py` or `*_test.py` files** found anywhere in the repository.
- **No `tests/` directory** exists.
- **No `conftest.py`** or pytest configuration.
- **No CI/CD test pipeline** (no `.github/workflows/`, no `Makefile` test targets).
- **No test dependencies** listed in `pyproject.toml` (no pytest, pytest-asyncio, etc.).

### Missing Test Infrastructure
- No `pytest.ini`, `pyproject.toml [tool.pytest]`, or `setup.cfg [tool:pytest]` configuration.
- No mocking utilities or fixtures for the `discord.Client` object.
- No test fixtures for `mcp.types` content objects.

---

## Gaps by Priority

### P0 — Critical Paths (No Tests, High Risk)

These are the most dangerous gaps. Failures here could cause silent data loss, account bans, or security issues.

#### 1. Message Operations (`tools/messages.py`) — 5 handlers, 0 tests

| Handler | Risk | Untested Paths |
|---|---|---|
| `send_message` | **CRITICAL** — sends messages as the user's account | Channel not found, Forbidden access, non-messageable channel, successful send |
| `read_messages` | **HIGH** — reads private messages | Empty channel, pagination, embed formatting, rate limiting |
| `search_messages` | **HIGH** | No results, query matching (case-insensitive), embed text search, limit handling |
| `edit_message` | **CRITICAL** — modifies user's messages | Editing other users' messages (should fail), message not found |
| `delete_message` | **CRITICAL** — irreversible action | Message not found, permission denied, successful deletion |

**Key concerns:**
- No validation that `send_message` won't send to DM channels unexpectedly.
- `edit_message` checks `message.author.id != client.user.id` — this guard must be tested.
- `search_messages` fetches `limit * 2` messages then filters — could be a performance/amplification vector.
- All handlers return `TextContent` on error instead of raising — callers can't distinguish success from failure programmatically.

#### 2. Authentication & Token Handling (`main.py`, `bot.py`, `setup.py`) — 0 tests

| Area | Risk | Untested Paths |
|---|---|---|
| `run_app()` missing `DISCORD_TOKEN` | **CRITICAL** — silent failure | Returns without error when token is missing |
| `SelfBot.on_ready()` | **MEDIUM** | `client.user` is None edge case |
| `solve_captcha()` | **HIGH** | Missing `GEMINI_API_KEY`, captcha solver failure, solver not initialized |
| `setup.py` `get_token_from_browser()` | **HIGH** | Playwright not installed, browser extraction failure |
| Token masking in logs | **LOW** | Short tokens not truncated properly |

**Key concerns:**
- `run_app()` silently returns if `DISCORD_TOKEN` is not set — no exception, no exit code.
- `solve_captcha()` raises `Exception("GEMINI_API_KEY not set")` — should be a specific exception type.
- `bot.py` has a protobuf compatibility monkey-patch at import time — untested.

#### 3. Tool Registry (`tools/registry.py`) — 0 tests

| Function | Risk | Untested Paths |
|---|---|---|
| `register()` | **HIGH** — all tools depend on this | Decorator returns original function, duplicate name registration, schema validation |
| `get_tool_definitions()` | **MEDIUM** | Empty registry, correct Tool object construction |
| `call_tool()` | **HIGH** | Unknown tool name raises `ValueError`, handler execution, handler exceptions |

**Key concerns:**
- `call_tool` raises `ValueError` for unknown tools, but all tool handlers catch `Exception` internally — inconsistency in error handling.
- No validation of `input_schema` structure.
- Module-level `registry = ToolRegistry()` singleton — hard to reset between tests.

#### 4. Interactions (`tools/interactions.py`) — 3 handlers, 0 tests

| Handler | Risk | Untested Paths |
|---|---|---|
| `send_slash_command` | **HIGH** — executes Discord commands | Command name parsing (`/` prefix), subcommand traversal, multiple matching commands, application_id filtering |
| `click_button` | **HIGH** — triggers button actions | Disabled buttons, URL buttons, row/column matching, custom_id matching, no buttons on message |
| `select_menu` | **HIGH** — selects menu options | Value validation, string→list coercion, options matching by value vs label, no options in menu |

**Key concerns:**
- `send_slash_command` has complex subcommand traversal logic (lines 114-147) — completely untested.
- `click_button` iterates components — if message has no components, silently returns "Button not found".
- `select_menu` coerces string values to list — potential edge case with non-string, non-list input.

---

### P1 — Important Features (No Tests, Moderate Risk)

#### 5. Rate Limiter (`rate_limiter.py`) — 0 tests

| Function | Untested Paths |
|---|---|
| `RateLimiter.__init__()` | Config loading from env vars, default config values |
| `_load_from_env()` | Parsing env vars, invalid values, missing vars |
| `wait_if_needed("message")` | Per-minute limit, per-second limit, cooldown state, sleep timing |
| `wait_if_needed("action")` | Per-minute limit, min action interval, cooldown state |
| `_clean_timestamps()` | Stale entry removal, boundary values |
| `_trigger_cooldown()` | Cooldown value set, print output |
| `reset()` | State cleared |
| `get_stats()` | Correct statistics returned |
| `get_rate_limiter()` | Singleton behavior |

**Key concerns:**
- Uses `threading.Lock` in async code — `await asyncio.sleep()` inside `with self._lock:` — this blocks the event loop thread while sleeping, defeating the purpose of async. This is a **bug** that tests would catch.
- `_trigger_cooldown` uses `print()` instead of `logging` — inconsistent with `main.py`.
- `_clean_timestamps` is called with `window=1` for messages but the result is never used — dead code on line 64.
- `get_rate_limiter()` is a module-level singleton — not thread-safe for initialization.

#### 6. Channel Operations (`tools/channels.py`) — 3 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `create_channel` | Text vs voice creation, category assignment, invalid type, guild not found |
| `delete_channel` | Channel not found, successful deletion |
| `list_channels` | Empty guild, channel type display, guild not found |

#### 7. Guild Operations (`tools/guilds.py`) — 2 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `list_guilds` | Bot not ready, empty guild list, guild name formatting |
| `get_user_info` | Bot not ready, user attributes |

#### 8. Member Operations (`tools/members.py`) — 5 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `kick_member` | Guild not found, member not found (cache miss), kick with reason |
| `ban_member` | Guild not found, ban with delete_message_days |
| `unban_member` | Guild not found, user not banned |
| `add_role` | Role not found, member not found, guild not found |
| `remove_role` | Same as add_role |

**Key concerns:**
- `add_role` and `remove_role` don't check if `guild` is `None` before calling `guild.get_member()` — will raise `AttributeError`.
- `kick_member` uses `or` for cache miss: `guild.get_member(user_id) or await guild.fetch_member(user_id)` — if `get_member` returns a falsey object, it falls through.

#### 9. Discrawl Integration (`tools/discrawl.py`) — 8 handlers, 0 tests

| Handler/Function | Untested Paths |
|---|---|
| `_text()` | Correct `TextContent` construction |
| `_resolve_discrawl_binary()` | Env var override, argument override, default |
| `_truncate_output()` | Under limit, at limit, over limit |
| `_binary_exists()` | Found via `shutil.which`, found via Path, not found, empty string |
| `_run_discrawl()` | Missing command, invalid args, invalid timeout, binary not found, timeout expired, successful run, stderr only |
| `_base_discrawl_arguments()` | Argument forwarding, None filtering |
| `_append_value()` | String conversion, empty string skipped, non-empty appended |
| `discrawl_search` | Missing query, empty query, all flag combinations |
| `discrawl_mentions` | Invalid type validation, valid type normalization |
| `discrawl_sync` | All flag combinations (full, with_embeddings, guild, guilds, etc.) |
| `discrawl_messages` | All flag combinations |

**Key concerns:**
- `_run_discrawl` spawns subprocesses — needs careful mocking.
- Timeout validation allows 5-1800 seconds but `DEFAULT_TIMEOUT_SECONDS = 180` — boundary tests needed.
- `discrawl_mentions` validates `type` but modifies the input dict in-place (`arguments = dict(arguments)` at line 492) — creates a shallow copy, which may not protect the original.
- `_truncate_output` appends `"\n... output truncated ..."` making output exceed `MAX_OUTPUT_CHARS` — off-by-one potential.

#### 10. Embed Formatting (`tools/embed.py`) — 0 tests

| Function | Untested Paths |
|---|---|
| `format_embed()` | All embed fields (title, author, description, fields, thumbnail, image, footer), empty embed, non-Embed input, None fields |

---

### P2 — Nice-to-Have Coverage (No Tests, Lower Risk)

#### 11. Voice Operations (`tools/voice.py`) — 2 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `join_voice_channel` | Non-voice channel, channel not found, successful join |
| `leave_voice_channel` | Not in voice, guild not found, successful leave |

#### 12. Presence (`tools/presence.py`) — 2 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `set_status` | Invalid status string, valid status mapping |
| `set_activity` | Invalid type, valid type mapping |

#### 13. Reactions (`tools/reactions.py`) — 2 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `add_reaction` | Unicode emoji, custom emoji, message not found |
| `remove_reaction` | Self removal, user-specified removal |

#### 14. Invites (`tools/invites.py`) — 3 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `create_invite` | Default values (24h, unlimited), custom values, channel not found |
| `list_invites` | No invites, guild not found |
| `delete_invite` | Invalid code, invite not found |

#### 15. Relationships (`tools/relationships.py`) — 4 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `list_friends` | Empty list, `AttributeError` on `client.friends`, populated list |
| `send_friend_request` | User found in cache with discriminator, new username system (discrim="0"), user not found |
| `add_friend` | User not found, successful add |
| `remove_friend` | User not found, successful remove |

**Key concerns:**
- `send_friend_request` has convoluted discriminator matching logic (lines 48-56) — the condition `user.discriminator == "0" or not discriminator` always evaluates to True when `discriminator` is None (the `else` branch), making the `discriminator == "0"` check redundant.

#### 16. Threads (`tools/threads.py`) — 5 handlers, 0 tests

| Handler | Untested Paths |
|---|---|
| `create_thread` | With/without message_id, channel not found |
| `archive_thread` | Non-thread channel, archive/unarchive |
| `read_thread_messages` | Empty thread, non-thread channel, thread not found |
| `list_active_threads` | No threads, channel not found, channel without threads support |
| `send_thread_message` | Non-thread channel, thread not found |

#### 17. Profile (`tools/profile.py`) — 1 handler, 0 tests

| Handler | Untested Paths |
|---|---|
| `edit_profile` | Bio only, accent_color mapping (uses `accent_colour` kwarg), empty arguments |

#### 18. Captcha Solver (`captcha/solver.py`) — 0 tests

| Function | Untested Paths |
|---|---|
| `HCaptchaSolver.__init__()` | Default values, proxy parsing |
| `_get_playwright_proxy()` | No proxy, proxy with auth (`user:pass@host:port`), proxy without auth |
| `_ensure_initialized()` | Double initialization guard, playwright setup |
| `solve()` | Success path, token not found, exception handling |
| `close()` | Page cleanup, playwright stop |

#### 19. Setup Script (`setup.py`) — 0 tests

| Function | Untested Paths |
|---|---|
| `_detect_default_command()` | Command found via `shutil.which`, fallback to python3 |
| `_default_client_config_candidates()` | Platform-specific paths (macOS, Windows, Linux) |
| `_read_json()` / `_write_json()` | File I/O, invalid JSON |
| `_backup_file()` | Non-existent file, existing file |
| `_upsert_server()` | `opencode-mcp` mode, `mcpServers` mode, existing config merge |
| `generate_config()` | Correct output format |

#### 20. Daemon (`scripts/daemon.py`) — 0 tests

| Function | Untested Paths |
|---|---|
| `_parse_after_time()` | All formats (relative, ISO, unix timestamp, invalid) |
| `handle_command()` | All ~18 command dispatches |
| `_list_guilds()`, `_list_channels()`, etc. | All data retrieval methods |

#### 21. CLI Client (`scripts/dcli.py`) — 0 tests

| Function | Untested Paths |
|---|---|
| `format_messages()` | Time parsing, timezone handling, empty messages |
| `send_request()` | Socket communication, timeout, connection failure |
| All `cmd_*` functions | Output formatting, error handling |

---

## Suggested Test Cases

### P0 Test Cases

#### `tools/messages.py`

```python
# test_send_message_success
async def test_send_message_success(mock_client):
    """Verify message is sent to correct channel and returns message_id."""
    mock_channel = AsyncMock()
    mock_channel.send.return_value = MagicMock(id=12345)
    mock_client.get_channel.return_value = mock_channel
    
    result = await send_message({"channel_id": "999", "content": "hello"})
    assert result[0].text == "Message sent to 999 (message_id=12345)"

# test_send_message_channel_not_found
async def test_send_message_channel_not_found(mock_client):
    """Returns 'Channel not found' when channel doesn't exist."""
    mock_client.get_channel.return_value = None
    mock_client.fetch_channel.side_effect = discord.NotFound(MagicMock(), {})
    
    result = await send_message({"channel_id": "999", "content": "hello"})
    assert "not found" in result[0].text.lower()

# test_send_message_forbidden
async def test_send_message_forbidden(mock_client):
    """Returns 'Access denied' when Discord raises Forbidden."""
    mock_client.get_channel.return_value = None
    mock_client.fetch_channel.side_effect = discord.Forbidden(MagicMock(), {})
    
    result = await send_message({"channel_id": "999", "content": "hello"})
    assert "access denied" in result[0].text.lower()

# test_send_message_non_messageable
async def test_send_message_non_messageable(mock_client):
    """Returns error when channel is not messageable."""
    mock_client.get_channel.return_value = MagicMock(spec=discord.CategoryChannel)
    
    result = await send_message({"channel_id": "999", "content": "hello"})
    assert "not messageable" in result[0].text.lower()

# test_edit_message_other_user
async def test_edit_message_other_user(mock_client):
    """Cannot edit messages authored by other users."""
    mock_channel = AsyncMock()
    mock_message = MagicMock()
    mock_message.author.id = 11111  # Different user
    mock_message.edit = AsyncMock()
    mock_client.user.id = 22222
    mock_channel.fetch_message.return_value = mock_message
    mock_client.get_channel.return_value = mock_channel
    
    result = await edit_message({"channel_id": "999", "message_id": "555", "content": "edited"})
    assert "Cannot edit" in result[0].text

# test_read_messages_with_embeds
async def test_read_messages_with_embeds(mock_client):
    """Messages with embeds include formatted embed text."""
    # ... verify format_embed is called and output includes [Embed]

# test_read_messages_empty_channel
async def test_read_messages_empty_channel(mock_client):
    """Returns empty string (or newline) when channel has no messages."""

# test_search_messages_case_insensitive
async def test_search_messages_case_insensitive(mock_client):
    """Search is case-insensitive."""

# test_delete_message_success
async def test_delete_message_success(mock_client):
    """Returns confirmation after deletion."""

# test_delete_message_not_found
async def test_delete_message_not_found(mock_client):
    """Handles message not found gracefully."""
```

#### `tools/registry.py`

```python
def test_register_adds_tool_and_handler():
    """Registering a tool adds it to both tools and handlers dicts."""
    reg = ToolRegistry()
    async def handler(args): return []
    reg.register("test_tool", "A test", {"type": "object"})(handler)
    assert "test_tool" in reg.tools
    assert reg.handlers["test_tool"] is handler

def test_register_returns_original_function():
    """Decorator returns the original function unchanged."""
    reg = ToolRegistry()
    async def handler(args): return []
    result = reg.register("t", "d", {})(handler)
    assert result is handler

async def test_call_tool_unknown_raises():
    """Calling unknown tool raises ValueError."""
    reg = ToolRegistry()
    with pytest.raises(ValueError, match="not found"):
        await reg.call_tool("nonexistent", {})

async def test_call_tool_delegates_to_handler():
    """call_tool invokes the correct handler with arguments."""
    reg = ToolRegistry()
    called_with = {}
    async def handler(args):
        called_with.update(args)
        return [TextContent(type="text", text="ok")]
    reg.register("t", "d", {})(handler)
    await reg.call_tool("t", {"key": "val"})
    assert called_with == {"key": "val"}

def test_get_tool_definitions_empty():
    """Returns empty list for empty registry."""
    reg = ToolRegistry()
    assert reg.get_tool_definitions() == []

def test_get_tool_definitions_returns_all():
    """Returns all registered tools."""
    reg = ToolRegistry()
    async def h(args): return []
    reg.register("a", "A", {})(h)
    reg.register("b", "B", {})(h)
    defs = reg.get_tool_definitions()
    assert len(defs) == 2
```

#### `main.py`

```python
async def test_run_app_no_token():
    """run_app returns early if DISCORD_TOKEN is not set."""
    # Patch os.getenv to return None
    # Verify function returns without error

async def test_list_tools_returns_definitions():
    """list_tools returns tool definitions from registry."""
    # Verify registry.get_tool_definitions() is called

async def test_call_tool_delegates():
    """call_tool delegates to registry.call_tool."""
    # Verify registry.call_tool is called with correct args
```

#### `tools/interactions.py`

```python
async def test_send_slash_command_strips_prefix():
    """Leading / is stripped from command name."""

async def test_send_slash_command_not_found():
    """Returns error when command not found in channel."""

async def test_send_slash_command_ambiguous():
    """Returns error with choices when multiple commands match and no app_id."""

async def test_click_button_disabled():
    """Disabled buttons are skipped."""

async def test_click_button_url():
    """URL buttons return the URL string."""

async def test_select_menu_string_coercion():
    """String values are coerced to list."""

async def test_select_menu_invalid_values():
    """Values not in menu options return error with available options."""

async def test_select_menu_no_specifier():
    """Defaults to first menu when no custom_id or row/column given."""
```

### P1 Test Cases

#### `rate_limiter.py`

```python
def test_rate_limit_config_defaults():
    """Default config has expected values."""
    cfg = RateLimitConfig()
    assert cfg.enabled is False
    assert cfg.messages_per_minute == 10

def test_load_from_env():
    """Config loads from environment variables."""
    with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": "true", "RATE_LIMIT_MESSAGES_PER_MINUTE": "20"}):
        cfg = RateLimiter._load_from_env()
        assert cfg.enabled is True
        assert cfg.messages_per_minute == 20

async def test_wait_if_needed_disabled():
    """Does nothing when rate limiting is disabled."""
    config = RateLimitConfig(enabled=False)
    rl = RateLimiter(config)
    # Should return immediately
    await rl.wait_if_needed("message")

async def test_message_per_second_limit():
    """Sleeps when messages per second limit is reached."""
    config = RateLimitConfig(enabled=True, messages_per_second=1)
    rl = RateLimiter(config)
    rl._message_timestamps.append(time.time())
    # Second call should trigger sleep
    await rl.wait_if_needed("message")

async def test_message_per_minute_triggers_cooldown():
    """Triggers cooldown when per-minute limit is reached."""
    config = RateLimitConfig(enabled=True, messages_per_minute=2, cooldown_on_limit=60)
    rl = RateLimiter(config)
    rl._message_timestamps = [time.time(), time.time()]
    await rl.wait_if_needed("message")
    assert rl.get_cooldown_remaining() > 0

def test_reset_clears_state():
    """Reset clears all timestamps and cooldown."""
    config = RateLimitConfig(enabled=True)
    rl = RateLimiter(config)
    rl._message_timestamps = [1.0, 2.0]
    rl._cooldown_until = time.time() + 60
    rl.reset()
    assert rl._message_timestamps == []
    assert rl.get_cooldown_remaining() == 0

def test_get_stats():
    """Stats returns correct structure."""
    config = RateLimitConfig(enabled=True)
    rl = RateLimiter(config)
    stats = rl.get_stats()
    assert "enabled" in stats
    assert "cooldown_remaining" in stats
    assert "config" in stats

def test_singleton_rate_limiter():
    """get_rate_limiter returns same instance."""
    # Reset global
    import discord_py_self_mcp.rate_limiter as rl_mod
    rl_mod._global_rate_limiter = None
    r1 = get_rate_limiter()
    r2 = get_rate_limiter()
    assert r1 is r2
```

#### `tools/discrawl.py`

```python
def test_text_helper():
    """_text creates correct TextContent."""
    result = _text("hello")
    assert len(result) == 1
    assert result[0].type == "text"
    assert result[0].text == "hello"

def test_truncate_output_under_limit():
    """Short strings are not truncated."""
    assert _truncate_output("short") == "short"

def test_truncate_output_over_limit():
    """Long strings are truncated with suffix."""
    long_text = "x" * (MAX_OUTPUT_CHARS + 100)
    result = _truncate_output(long_text)
    assert len(result) > MAX_OUTPUT_CHARS  # suffix adds length
    assert "truncated" in result

def test_binary_exists_found():
    """_binary_exists returns True for known binaries."""
    assert _binary_exists("ls") is True

def test_binary_exists_not_found():
    """_binary_exists returns False for nonexistent binary."""
    assert _binary_exists("nonexistent_binary_xyz") is False

def test_binary_exists_empty():
    """_binary_exists returns False for empty string."""
    assert _binary_exists("") is False

async def test_run_discrawl_missing_command():
    """Returns error when command is missing."""
    result = await _run_discrawl({"command": ""})
    assert "Missing" in result[0].text

async def test_run_discrawl_invalid_args():
    """Returns error when args is not a list of strings."""
    result = await _run_discrawl({"command": "test", "args": [123]})
    assert "array of strings" in result[0].text

async def test_run_discrawl_invalid_timeout():
    """Returns error for out-of-range timeout."""
    result = await _run_discrawl({"command": "test", "timeout_seconds": 2})
    assert "between 5 and 1800" in result[0].text

def test_base_discrawl_arguments():
    """_base_discrawl_arguments correctly forwards args."""
    result = _base_discrawl_arguments(
        {"config_path": "/tmp/c", "binary": "discrawl", "timeout_seconds": 60, "extra": "ignored"},
        "sync", ["--full"]
    )
    assert result["command"] == "sync"
    assert result["args"] == ["--full"]
    assert result["config_path"] == "/tmp/c"
    assert "extra" not in result

def test_append_value():
    """_append_value adds flag and value to args list."""
    args = []
    _append_value(args, "--guild", "123")
    assert args == ["--guild", "123"]

def test_append_value_empty_skipped():
    """_append_value skips empty/whitespace values."""
    args = []
    _append_value(args, "--guild", "  ")
    assert args == []

async def test_discrawl_mentions_invalid_type():
    """Returns error for invalid mention type."""
    result = await discrawl_mentions({"type": "invalid"})
    assert "must be" in result[0].text
```

#### `tools/members.py`

```python
async def test_add_role_no_guild():
    """add_role returns error or raises when guild is None."""
    # Currently has a bug: no null check on guild before guild.get_member()

async def test_kick_member_not_found():
    """Returns error when member is not in guild."""

async def test_ban_member_uses_discord_object():
    """Bans by creating a discord.Object with user_id."""
```

#### `tools/embed.py`

```python
def test_format_embed_empty():
    """Empty embed returns empty string."""
    embed = discord.Embed()
    assert format_embed(embed) == ""

def test_format_embed_non_embed():
    """Non-Embed input returns empty string."""
    assert format_embed("not an embed") == ""

def test_format_embed_full():
    """Embed with all fields returns all parts."""
    embed = discord.Embed(title="T", description="D")
    embed.set_author(name="Author")
    embed.add_field(name="F", value="V")
    embed.set_thumbnail(url="https://example.com/thumb.png")
    embed.set_image(url="https://example.com/image.png")
    embed.set_footer(text="Footer")
    result = format_embed(embed)
    assert "[Title]: T" in result
    assert "[Author]: Author" in result
    assert "[Description]: D" in result
    assert "[Field: F]: V" in result
    assert "[Thumbnail]" in result
    assert "[Image]" in result
    assert "[Footer]: Footer" in result

def test_format_embed_none_fields():
    """Embed with None optional fields doesn't crash."""
    embed = discord.Embed(title="T")
    # author, footer, thumbnail, image are None by default
    result = format_embed(embed)
    assert "[Title]: T" in result
```

### P2 Test Cases

#### `captcha/solver.py`

```python
def test_proxy_parsing_with_auth():
    """_get_playwright_proxy parses user:pass@host:port."""
    solver = HCaptchaSolver(proxy="user:pass@1.2.3.4:8080")
    result = solver._get_playwright_proxy()
    assert result == {"server": "http://1.2.3.4:8080", "username": "user", "password": "pass"}

def test_proxy_parsing_without_auth():
    """_get_playwright_proxy parses host:port without auth."""
    solver = HCaptchaSolver(proxy="1.2.3.4:8080")
    result = solver._get_playwright_proxy()
    assert result == {"server": "http://1.2.3.4:8080"}

def test_proxy_parsing_none():
    """_get_playwright_proxy returns None when no proxy."""
    solver = HCaptchaSolver()
    assert solver._get_playwright_proxy() is None
```

#### `setup.py`

```python
def test_generate_config():
    """generate_config produces correct MCP config structure."""
    config = generate_config("test-token-123")
    assert "mcpServers" in config
    assert "discord-py-self" in config["mcpServers"]
    entry = config["mcpServers"]["discord-py-self"]
    assert entry["env"]["DISCORD_TOKEN"] == "test-token-123"

def test_upsert_server_mcpServers_mode():
    """_upsert_server creates correct structure for mcpServers mode."""
    result = _upsert_server({}, "token123", "mcpServers")
    assert "mcpServers" in result
    assert "discord-py-self" in result["mcpServers"]

def test_upsert_server_opencode_mode():
    """_upsert_server creates correct structure for opencode-mcp mode."""
    result = _upsert_server({}, "token123", "opencode-mcp")
    assert "mcp" in result
    assert "discord-py-self" in result["mcp"]

def test_backup_file_nonexistent():
    """_backup_file returns None for non-existent file."""
    result = _backup_file("/tmp/nonexistent_file_xyz.json")
    assert result is None

def test_detect_default_command():
    """_detect_default_command returns a tuple of (command, args)."""
    cmd, args = _detect_default_command()
    assert isinstance(cmd, str)
    assert isinstance(args, list)
```

#### `scripts/daemon.py`

```python
def test_parse_after_time_relative_hours():
    """Parses '4h' correctly."""
    dt = DiscordDaemon()._parse_after_time("4h")
    assert dt is not None
    assert dt < datetime.now(timezone.utc)

def test_parse_after_time_relative_minutes():
    """Parses '30m' correctly."""

def test_parse_after_time_relative_days():
    """Parses '1d' correctly."""

def test_parse_after_time_iso():
    """Parses ISO datetime correctly."""

def test_parse_after_time_unix():
    """Parses unix timestamp correctly."""

def test_parse_after_time_invalid():
    """Returns None for invalid input."""
    assert DiscordDaemon()._parse_after_time("invalid") is None

def test_parse_after_time_none():
    """Returns None for None input."""
    assert DiscordDaemon()._parse_after_time(None) is None
```

---

## Recommended Testing Framework Setup

### 1. Dependencies to Add

```toml
# pyproject.toml — add to [project] dependencies or create optional group
[project.optional-dependencies]
test = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "pytest-mock>=3.12",
    "unittest-mock; python_version < '3.13'",
]
```

### 2. Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["discord_py_self_mcp"]
omit = ["tests/*", "scripts/*"]

[tool.coverage.report]
fail_under = 60
show_missing = true
```

### 3. Directory Structure

```
discord-py-self-mcp/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_rate_limiter.py     # P1 — standalone, no Discord dependency
│   ├── test_registry.py         # P0 — standalone, no Discord dependency
│   ├── test_embed.py            # P2 — standalone, needs discord.Embed
│   ├── test_discrawl.py         # P1 — mostly standalone helpers
│   ├── test_messages.py         # P0 — needs mock discord.Client
│   ├── test_channels.py         # P1
│   ├── test_guilds.py           # P1
│   ├── test_members.py          # P1
│   ├── test_interactions.py     # P0
│   ├── test_presence.py         # P2
│   ├── test_voice.py            # P2
│   ├── test_reactions.py        # P2
│   ├── test_invites.py          # P2
│   ├── test_relationships.py    # P2
│   ├── test_threads.py          # P2
│   ├── test_profile.py          # P2
│   ├── test_main.py             # P0
│   ├── test_bot.py              # P0
│   ├── test_setup.py            # P2
│   ├── test_captcha_solver.py   # P2
│   └── scripts/
│       ├── test_daemon.py       # P2
│       └── test_dcli.py         # P2
```

### 4. Key Fixtures (`conftest.py`)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

@pytest.fixture
def mock_client():
    """Create a mock discord.Client with common methods."""
    with patch("discord_py_self_mcp.bot.client") as mock:
        mock.user = MagicMock()
        mock.user.id = 123456789
        mock.user.name = "TestUser"
        mock.user.discriminator = "0001"
        mock.is_ready.return_value = True
        mock.get_channel.return_value = None
        mock.fetch_channel = AsyncMock()
        mock.get_guild.return_value = None
        mock.guilds = []
        yield mock

@pytest.fixture
def mock_messageable_channel():
    """A channel that implements discord.abc.Messageable."""
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 999
    channel.name = "test-channel"
    channel.send = AsyncMock(return_value=MagicMock(id=111222))
    channel.history = AsyncMock()
    channel.fetch_message = AsyncMock()
    return channel

@pytest.fixture
def mock_guild():
    """A mock Discord guild."""
    guild = MagicMock()
    guild.id = 888
    guild.name = "Test Guild"
    guild.channels = []
    guild.members = []
    guild.get_member.return_value = None
    guild.fetch_member = AsyncMock()
    return guild

@pytest.fixture
def fresh_registry():
    """Create a fresh ToolRegistry for isolated tests."""
    from discord_py_self_mcp.tools.registry import ToolRegistry
    return ToolRegistry()
```

### 5. Recommended Test Order (Implementation Priority)

1. **Start with P1 pure-logic modules** (no Discord dependency):
   - `test_rate_limiter.py` — fully testable without mocking
   - `test_registry.py` — fully testable without mocking
   - `test_discrawl.py` — helpers are pure functions
   - `test_embed.py` — pure function with discord.Embed

2. **Then P0 tool handlers** (need mock client):
   - `test_messages.py` — most critical, 5 handlers
   - `test_interactions.py` — complex logic, 3 handlers
   - `test_main.py` — entry point

3. **Then P1 tool handlers**:
   - `test_channels.py`, `test_guilds.py`, `test_members.py`

4. **Finally P2 modules**:
   - `test_presence.py`, `test_voice.py`, etc.

### 6. Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest

# Run with coverage
pytest --cov=discord_py_self_mcp --cov-report=term-missing

# Run specific priority
pytest tests/test_rate_limiter.py tests/test_registry.py  # P1 first
pytest tests/test_messages.py tests/test_interactions.py  # P0 critical
```

---

## Bugs Found During Analysis

1. **RateLimiter uses `threading.Lock` with `await asyncio.sleep()`** — The lock blocks the event loop thread while the coroutine sleeps, preventing other async tasks from running. Should use `asyncio.Lock`.

2. **`tools/members.py` `add_role`/`remove_role` — Missing guild null check** — Lines 121 and 152 call `guild.get_member()` without checking if `guild` is `None` first (unlike `kick_member` which checks).

3. **`tools/discrawl.py` `_trigger_cooldown` uses `print()` instead of logging** — Inconsistent with `main.py` which configures `logging`.

4. **`tools/relationships.py` `send_friend_request` — Redundant condition** — Line 54: `user.discriminator == "0" or not discriminator` — the `or not discriminator` part is always True in the else branch (where `discriminator` is None), making the `discrim == "0"` check unreachable.

5. **`rate_limiter.py` line 64 — Dead code** — `_clean_timestamps(self._message_timestamps, 1)` result is computed but never used. The per-second filtering happens separately on lines 69-71.

6. **`rate_limiter.py` `_trigger_cooldown` doesn't await** — When the per-minute limit is hit, `_trigger_cooldown` is called (which just sets a value and prints) but `wait_if_needed` returns immediately without actually waiting for the cooldown. The caller proceeds unaware that the cooldown was triggered.

---

## Summary Statistics

| Priority | Modules | Handlers | Suggested Test Cases |
|---|---|---|---|
| P0 | 4 | 8 | ~30 |
| P1 | 6 | 18 | ~40 |
| P2 | 11 | ~24 | ~35 |
| **Total** | **21** | **~50** | **~105** |

**Estimated effort to reach 60% coverage:** ~40 test cases covering P0 + P1.  
**Estimated effort to reach 80% coverage:** ~75 test cases covering P0 + P1 + core P2.
