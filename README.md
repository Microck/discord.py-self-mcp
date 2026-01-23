<p align="center">
  <img src="./logo.png" alt="discord-py-self-mcp" width="100">
</p>

<h1 align="center">discord-py-self-mcp</h1>

<p align="center">
  comprehensive discord selfbot mcp server for full user autonomy.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/language-python-blue" alt="language">
  <img src="https://img.shields.io/badge/mcp-sdk-orange" alt="mcp">
  <a href="https://github.com/Microck/opencode-studio"><img src="https://img.shields.io/badge/opencode-studio-brown?logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAABiElEQVR4nF2Sv0tWcRTGPyeVIpCWwmyJGqQagsqCsL2hhobsD3BvdWhoj/6CiIKaoqXBdMjKRWwQgqZ%2BokSvkIhg9BOT9xPn9Vx79cD3cu6953zP8zznCQB1V0S01d3AKeAKcBVYA94DjyJioru2k9SHE%2Bqc%2Bkd9rL7yf7TUm%2BpQ05yPUM%2Bo626Pp%2BqE2q7GGfWrOpjNnWnAOPAGeAK8Bb4U5D3AJ%2BAQsAAMAHfVvl7gIrAf2Kjiz8BZYB3YC/wFpoGDwHfgEnA0oU7tgHiheEShyXxY/Vn/n6ljye8DcBiYAloRcV3tAdrV1xMRG%2Bo94DywCAwmx33AJHASWK7iiAjzNFOBl7WapPYtYdyo8RlLqVpOVPvq9KoH1NUuOneycaRefqnP1ftdUyiOt5KS%2BqLWdDpVzTXMl5It4Jr6u%2BQ/nhyBc8C7jpowGxGvmxuPqT9qyYuFIKdP71B8WT3SOKexXLrntvqxq3BefaiuFMQ0wqZftxl3M78MjBasfiDN/SAi0kFbtf8ACtKBWZBDoJEAAAAASUVORK5CYII%3D" alt="Add with OpenCode Studio" /></a>
</p>


---
### overview

discord-py-self-mcp acts as a bridge between your AI assistant (Claude Code, Opencode, Codex, etc) and your personal Discord account. unlike standard bots, this "selfbot" runs as you; allowing your AI to read your DMs, reply to friends, manage your servers, and interact with buttons/menus just like a human user.

built on the <a href="https://github.com/dolfies/discord.py-self">discord.py-self</a> library by dolfies. it offers a safe, stable, and feature-rich interface for automating your daily discord life.

> **note**: automating user accounts is against the Discord ToS. use this at your own risk.

---

### quick installation

**codex**  
tell codex:  
```
Fetch and follow instructions from https://raw.githubusercontent.com/Microck/discord.py-self-mcp/refs/heads/master/.codex/INSTALL.md
```

**opencode**  
tell opencode:  
```
Fetch and follow instructions from https://raw.githubusercontent.com/Microck/discord.py-self-mcp/refs/heads/master/.opencode/INSTALL.md
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

### how it works (setup wizard)

run the interactive setup script to generate your config:

```bash
# if using uv
uv tool run discord-py-self-mcp-setup

# or running the script directly from the repo
python3 discord_py_self_mcp/setup.py
```

1. **extract token**: automatically grabs your token from an open browser session (playwright)
2. **generate config**: outputs the mcp configuration json for you
3. **configure**: paste the config into your mcp client settings

---

### manual configuration

add this to your MCP config (`claude_desktop_config.json`, `.opencode.json`, etc):

```json
{
  "mcpServers": {
    "discord-py-self": {
      "command": "uv",
      "args": ["tool", "run", "discord-py-self-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_token_here"
      }
    }
  }
}
```

if installed via pip/venv, adjust the command to point to your python executable or script location.

---

### features

powered by the robust `discord.py-self` library.

| category | tools | description |
|----------|-------|-------------|
| **system** | 2 | get_user_info, list_guilds |
| **messages** | 5 | send_message, read_messages, search_messages, edit_message, delete_message, pin/unpin |
| **channels** | 3 | create_channel, delete_channel, list_channels |
| **voice** | 2 | join_voice_channel, leave_voice_channel |
| **relationships** | 4 | list_friends, add_friend, remove_friend, send_friend_request |
| **presence** | 2 | set_status, set_activity |
| **interactions** | 3 | send_slash_command, click_button, select_menu |
| **threads** | 2 | create_thread, archive_thread |
| **members** | 4 | kick_member, ban_member, unban_member, add_role, remove_role |
| **invites** | 3 | create_invite, list_invites, delete_invite |
| **profile** | 1 | edit_profile (bio, accent) |
| **reactions** | 2 | add_reaction, remove_reaction |

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

automatically solves hCaptchas when encountered (e.g., joining servers, DMs).
built upon [ScremerMemer/hCaptcha-Solver](https://github.com/ScremerMemer/hCaptcha-Solver).

> **warning**: this feature is experimental. use at your own risk.

**requirements:**
1. **Groq API Key**: required for AI vision. set `GROQ_API_KEY` in environment.
2. **Camoufox**: required for browser fingerprinting.
   ```bash
   pip install camoufox[geoip]
   python -m camoufox fetch
   ```

**configuration:**
add to your environment variables:
```json
"GROQ_API_KEY": "gsk_..."
```

---

### troubleshooting

| problem | solution |
|---------|----------|
| **token invalid** | run the setup script again to extract a fresh one |
| **missing dependencies** | ensure `uv` or `pip` installed all requirements (`discord.py-self`, `mcp`, `playwright`) |
| **playwright error** | run `playwright install chromium` |
| **audioop error** | ensure `audioop-lts` is installed if using python 3.13+ |
| **voice error** | install `libffi-dev` (linux) or ensure PyNaCl built correctly |

---

### project structure

```
discord_py_self_mcp/
├── bot.py          # discord.py-self client instance
├── main.py         # mcp server entry point
├── setup.py        # setup wizard (token extraction)
└── tools/          # tool implementations
    ├── channels.py
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

### license

mit
