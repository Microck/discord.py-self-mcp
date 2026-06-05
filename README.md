<p align="center">
  <img src="./logo.png" alt="discord-py-self-mcp" width="100">
</p>

<h1 align="center">discord-py-self-mcp</h1>

<p align="center">
  comprehensive discord selfbot mcp server for full user autonomy.
</p>

<p align="center">
  <a href="https://github.com/Microck/discord.py-self-mcp/releases"><img src="https://img.shields.io/github/v/release/Microck/discord.py-self-mcp?display_name=tag&style=flat-square&label=release&color=000000" alt="release"></a>
  <a href="https://www.npmjs.com/package/discord-selfbot-mcp"><img src="https://flat.badgen.net/npm/dt/discord-selfbot-mcp?label=downloads&color=000000" alt="npm downloads"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-mit-000000?style=flat-square" alt="license"></a>
</p>

<p align="center">
<video src="https://github.com/user-attachments/assets/d7d9fc9f-c466-49c0-a666-05bed2fa8ca9
" controls preload="auto" width="100%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 800px;"></video>
</p>

---

## quick start

this is a local mcp server (stdio transport). your mcp client spawns it as a process, and you provide secrets (like `DISCORD_TOKEN`) via the client's `env`/`environment` config.

manual run:

```bash
DISCORD_TOKEN="your_discord_token_here" python3 -m discord_py_self_mcp.main
```

> **important:** automating user accounts is against the Discord ToS. use this at your own risk.

---

### overview

discord-py-self-mcp acts as a bridge between your ai assistant (Claude Code, OpenCode, Codex, etc) and your personal discord account. unlike standard bots, this "selfbot" runs as you; allowing your ai to read your dms, reply to friends, manage your servers, and interact with buttons/menus just like a human user.

built on the <a href="https://github.com/dolfies/discord.py-self">discord.py-self</a> library by dolfies.

---

### quick installation

paste this into your llm agent session:

```
Install and configure discord-selfbot-mcp by following the instructions here:
https://raw.githubusercontent.com/Microck/discord.py-self-mcp/refs/heads/master/INSTALL.md
```

**npm (recommended)**

```bash
npm install -g discord-selfbot-mcp
discord-selfbot-mcp-setup
```

---

### manual installation

**prerequisites**:
- python 3.10+
- `uv` (recommended) or `pip`
- **voice support (linux only)**: `libffi-dev` (or `libffi-devel`), `python-dev` (e.g. `python3-dev`)

**install**:

```bash
uv tool install git+https://github.com/Microck/discord.py-self-mcp.git
# or
pip install git+https://github.com/Microck/discord.py-self-mcp.git
```

> **note**: voice dependencies (PyNaCl) are included by default. on linux, ensure system packages are installed first.

---

### npm installation (node.js wrapper)

**prerequisites**:
- node.js 18+
- python 3.10+

**install**:

```bash
npm install -g discord-selfbot-mcp
```

the npm package is a wrapper that uses the underlying python implementation.

---

### how it works (setup wizard)

run the interactive setup script to extract your token and generate the mcp config json (it can also write to common client config files and creates a backup before editing).

```bash
# if using npm
discord-selfbot-mcp-setup

# if using python (uv/pip)
python3 -m discord_py_self_mcp.setup
```

1. **extract token**: grabs your token from an open browser session (playwright) or via manual entry
2. **generate config**: prints the mcp configuration json (and can write it to your client config)
3. **configure**: paste the config into your mcp client settings

---

### manual configuration

because this server uses `stdio`, you configure it as a local command and pass the token via `env` (not `url`/`headers`).

examples:
- `mcp.example.json`
- `mcp.python.example.json`
- `.env.example`

**npm wrapper (recommended)**:

```json
{
  "mcpServers": {
    "discord-py-self": {
      "command": "discord-selfbot-mcp",
      "env": {
        "DISCORD_TOKEN": "${DISCORD_TOKEN}"
      }
    }
  }
}
```

**python (uv tool)**:

```json
{
  "mcpServers": {
    "discord-py-self": {
      "command": "uv",
      "args": ["tool", "run", "discord-py-self-mcp"],
      "env": {
        "DISCORD_TOKEN": "${DISCORD_TOKEN}"
      }
    }
  }
}
```

**python (pip / venv)**:

```json
{
  "mcpServers": {
    "discord-py-self": {
      "command": "python3",
      "args": ["-m", "discord_py_self_mcp.main"],
      "env": {
        "DISCORD_TOKEN": "${DISCORD_TOKEN}"
      }
    }
  }
}
```

> if your client does not expand `${DISCORD_TOKEN}`, replace it with the literal token value.

---

### features

powered by the robust `discord.py-self` library.

| category | tools | description |
|----------|-------|-------------|
| **system** | 2 | get_user_info, list_guilds |
| **messages** | 6 | send_message, read_messages, search_messages, edit_message, delete_message, get_message_attachments |
| **channels** | 3 | create_channel, delete_channel, list_channels |
| **dms** | 1 | list_dm_channels |
| **voice** | 2 | join_voice_channel, leave_voice_channel |
| **relationships** | 4 | list_friends, send_friend_request, add_friend, remove_friend |
| **presence** | 2 | set_status, set_activity |
| **interactions** | 3 | send_slash_command, click_button, select_menu |
| **threads** | 5 | create_thread, send_thread_message, list_active_threads, read_thread_messages, archive_thread |
| **members** | 5 | kick_member, ban_member, unban_member, add_role, remove_role |
| **invites** | 3 | create_invite, list_invites, delete_invite |
| **profile** | 1 | edit_profile |
| **reactions** | 2 | add_reaction, remove_reaction |
| **discrawl** | 7 | run_discrawl, discrawl_doctor, discrawl_status, discrawl_sync, discrawl_search, discrawl_messages, discrawl_mentions |

### direct messages

`list_dm_channels` enumerates your open 1:1 and group DM channels so you can
discover a `channel_id` instead of needing to know it in advance. Each row is
`<channel_id> - [dm|group] <recipient display> (id=<user_id>) [BOT]`. Optional
args: `include_groups` (default `true`) and `name_contains` (case-insensitive
filter on recipient name/handle), e.g. find the DM with a person by name and
feed the id straight into `read_messages` / `send_message`.

### slash commands

`send_slash_command` invokes an application command in a channel or DM. Pass
`application_id` (the bot's user/application ID) for reliable resolution; in a DM
with a bot it is inferred automatically. The command and any options are
resolved from the application's registered command list
(`GET /applications/{id}/commands`), which works for ordinary guild-installed
bots whose commands the per-channel `/` search index does not return. Subcommands
are space-separated in `command_name` (e.g. `"config set"`). Example:

```json
{
  "channel_id": "123456789012345678",
  "command_name": "remind",
  "application_id": "987654321098765432",
  "options": { "text": "stand up", "when": "in 10 minutes" }
}
```

### discrawl integration

Use `run_discrawl` to execute local `discrawl` commands directly from MCP.
Use typed tools for common operations (`discrawl_sync`, `discrawl_search`, `discrawl_messages`, etc.) when you want structured params.
By default this MCP uses the Microck fork at `../discrawl-self/bin/discrawl`:
`https://github.com/Microck/discrawl-self`. It does not silently fall back to a
global `discrawl` from `PATH`; set `DISCRAWL_BIN` or the tool `binary` argument
when you intentionally want another executable.

Example tool call payload:

```json
{
  "command": "sync",
  "args": ["--guild", "1234567890", "--since", "2026-03-01T00:00:00Z"],
  "config_path": "~/.discrawl/config.toml"
}
```

Typed tool payload example:

```json
{
  "tool": "discrawl_sync",
  "args": {
    "guild": "1234567890",
    "since": "2026-03-01T00:00:00Z",
    "full": true,
    "config_path": "~/.discrawl/config.toml"
  }
}
```

Optional env var:

- `DISCRAWL_BIN` - custom path to discrawl executable. This overrides the default Microck fork lookup.

### attachment access

Use `get_message_attachments` when a message contains files or images you need to inspect directly.
It returns attachment metadata for the target message and can stream image/file content back through MCP outputs.

### comparison

| feature | discord-py-self-mcp | discord.py-self (Lib) | Maol-1997 | codebyyassine | elyxlz |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **read messages** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **send messages** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **list guilds** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **list channels** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **get user info** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **search messages** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **create channels** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **delete channels** | ✅ | ✅ | ❌ | ✅ | ❌ |
| **edit messages** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **delete messages** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **join voice** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **manage friends** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **manage threads** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **slash commands** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **click buttons** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **select menus** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **kick/ban** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **invites** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **profile edit** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **setup wizard** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **captcha solver** | ✅ | ❌ | ❌ | ❌ | ❌ |

✅ = supported

❌ = not supported

🚧 = planned / in progress

---

### captcha solving (experimental)

automatically solves hCaptchas when encountered (e.g., joining servers, dms).
built upon [QIN2DIM/hcaptcha-challenger](https://github.com/QIN2DIM/hcaptcha-challenger) - an AI-powered hCaptcha solver using vision models.

> **warning**: this feature is experimental. use at your own risk.

**requirements:**
1. **Gemini API Key**: Required for AI vision. Get from [Google AI Studio](https://aistudio.google.com/app/apikey). Set `GEMINI_API_KEY` in your mcp client `env`.
2. **Playwright**: Required for browser automation.
   ```bash
   playwright install chromium --with-deps
   ```

**optional:**
- `CAPTCHA_PROXY`: proxy url for solving hCaptcha challenges.
- `TEMP_DIR`: Directory for temporary model files (default: `/tmp/hcaptcha`)

---

### rate limiting (recommended)

built-in rate limiting to prevent account bans. configurable via environment variables.

**configuration:**

| variable | default | description |
|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable/disable rate limiting |
| `RATE_LIMIT_MESSAGES_PER_MINUTE` | `10` | Max messages per minute |
| `RATE_LIMIT_MESSAGES_PER_SECOND` | `1` | Max messages per second |
| `RATE_LIMIT_ACTIONS_PER_MINUTE` | `5` | Max actions (joins, etc.) per minute |
| `RATE_LIMIT_COOLDOWN` | `60` | Cooldown duration when limit hit (seconds) |

> rate limiting is enabled by default to reduce ban risk. Only disable it if you are deliberately taking responsibility for raw Discord API pacing yourself.

---

### troubleshooting

| problem | solution |
|---------|----------|
| **token invalid** | run the setup script again to extract a fresh one |
| **missing dependencies** | ensure `uv` or `pip` installed all requirements |
| **playwright error** | run `playwright install chromium` |
| **audioop error** | ensure `audioop-lts` is installed if using python 3.13+ |
| **camoufox missing** | run `python -m camoufox fetch` |
| **voice error** | install `libffi-dev` (linux) or ensure PyNaCl built correctly |

---

### project structure

```
discord_py_self_mcp/
├── bot.py
├── main.py
├── setup.py
├── rate_limiter.py
├── tool_utils.py
├── cli_runtime.py
├── logging_utils.py
├── captcha/
│   └── solver.py
└── tools/
    ├── channels.py
    ├── dms.py
    ├── discrawl.py
    ├── embed.py
    ├── guilds.py
    ├── interactions.py
    ├── invites.py
    ├── members.py
    ├── messages.py
    ├── presence.py
    ├── profile.py
    ├── reactions.py
    ├── registry.py
    ├── relationships.py
    ├── threads.py
    └── voice.py
```

---

### skill cli mode (optional)

in addition to the mcp server, this package also provides a **skill/cli mode** for command-line usage with a persistent daemon. this is useful for scripts or when you need faster execution without the mcp protocol overhead.

**quick start**:
```bash
# install (same package)
npm install -g discord-selfbot-mcp

# create .env file
echo "DISCORD_TOKEN=***" > .env

# use skill mode (from package directory)
python3 scripts/dcli.py send-message --channel 123 --content "Hello!"
```

**key commands**:
```bash
python3 scripts/dcli.py daemon start     # start the daemon
python3 scripts/dcli.py daemon status    # check daemon status
python3 scripts/dcli.py send-message --channel CHANNEL_ID --content "Hello"
python3 scripts/dcli.py list-guilds
python3 scripts/dcli.py read-messages --channel CHANNEL_ID --limit 20
python3 scripts/dcli.py get-message-attachments --channel CHANNEL_ID --message MESSAGE_ID
python3 scripts/dcli.py get-message-attachments --channel CHANNEL_ID --message MESSAGE_ID --download --output-dir ./attachments
```

**when to use skill mode**:
- command-line scripting
- faster execution (persistent connection)
- automation tasks
- when mcp is not needed

see [SKILL.md](SKILL.md) for detailed documentation.

---

### license

this project is licensed under the [mit license](./LICENSE).

---

### contributing

issues and pull requests are welcome at [github.com/Microck/discord.py-self-mcp](https://github.com/Microck/discord.py-self-mcp).

1. fork the repository
2. create a feature branch (`git checkout -b feature/my-feature`)
3. commit your changes (`git commit -m 'add my feature'`)
4. push to the branch (`git push origin feature/my-feature`)
5. open a pull request

please ensure tests pass (`pytest`) before submitting.
