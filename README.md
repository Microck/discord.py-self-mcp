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
  <img src="https://img.shields.io/badge/npm-%40discord--selfbot--mcp-orange" alt="npm">
  <img src="https://img.shields.io/badge/mcp-sdk-orange" alt="mcp">
  <a href="https://github.com/Microck/opencode-studio"><img src="https://img.shields.io/badge/opencode-studio-brown?logo=data%3Aimage%2Fpng%3Bbase64%2CiVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAABiElEQVR4nF2Sv0tWcRTGPyeVIpCWwmyJGqQagsqCsL2hhobsD3BvdWhoj/6CiIKaoqXBdMjKRWwQgqZ%2BokSvkIhg9BOT9xPn9Vx79cD3cu6953zP8zznCQB1V0S01d3AKeAKcBVYA94DjyJioru2k9SHE%2Bqc%2Bkd9rL7yf7TUm%2BpQ05yPUM%2Bo626Pp%2BqE2q7GGfWrOpjNnWnAOPAGeAK8Bb4U5D3AJ%2BAQsAAMAHfVvl7gIrAf2Kjiz8BZYB3YC/wFpoGDwHfgEnA0oU7tgHiheEShyXxY/Vn/n6ljye8DcBiYAloRcV3tAdrV1xMRG%2Bo94DywCAwmx33AJHASWK7iiAjzNFOBl7WapPYtYdyo8RlLqVpOVPvq9KoH1NUuOneycaRefqnP1ftdUyiOt5KS%2BqLWdDpVzTXMl5It4Jr6u%2BQ/nhyBc8C7jpowGxGvmxuPqT9qyYuFIKdP71B8WT3SOKexXLrntvqxq3BefaiuFMQ0wqZftxl3M78MjBasfiDN/SAi0kFbtf8ACtKBWZBDoJEAAAAASUVORK5CYII%3D" alt="Add with OpenCode Studio" /></a>
</p>

### demo video

<details>
<summary>Showcase</summary>

<p>See discord-py-self-mcp in action:</p>

<video src="./showcase.mp4" controls preload="auto" width="100%" style="border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); max-width: 800px;"></video>

<blockquote>
⚠️ <strong>Note:</strong> Video is locally referenced and won't render on GitHub. Clone the repository and view locally to see the demo.
</blockquote>

</details>

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
| **messages** | 5 | send_message, read_messages, search_messages, edit_message, delete_message |
| **channels** | 3 | create_channel, delete_channel, list_channels |
| **voice** | 2 | join_voice_channel, leave_voice_channel |
| **relationships** | 4 | list_friends, send_friend_request, add_friend, remove_friend |
| **presence** | 2 | set_status, set_activity |
| **interactions** | 3 | send_slash_command, click_button, select_menu |
| **threads** | 2 | create_thread, archive_thread |
| **members** | 5 | kick_member, ban_member, unban_member, add_role, remove_role |
| **invites** | 3 | create_invite, list_invites, delete_invite |
| **profile** | 1 | edit_profile |
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

automatically solves hCaptchas when encountered (e.g., joining servers, dms).
built upon [ScremerMemer/hCaptcha-Solver](https://github.com/ScremerMemer/hCaptcha-Solver).

> **warning**: this feature is experimental. use at your own risk.

**requirements:**
1. **Groq API Key**: required for ai vision. set `GROQ_API_KEY` in your mcp client `env`.
2. **Camoufox**: required for browser fingerprinting.
   ```bash
   python -m camoufox fetch
   ```

**optional:**
- `CAPTCHA_PROXY`: proxy url for solving hCaptcha challenges.

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
├── captcha/
│   ├── agent.py
│   ├── browser.py
│   ├── motion.py
│   └── solver.py
└── tools/
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
