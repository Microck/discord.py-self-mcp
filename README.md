<p align="center">
  <img src="./logo.png" alt="discord-selfbot-mcp" width="100">
</p>

<h1 align="center">discord-selfbot-mcp</h1>

<p align="center">
  comprehensive discord selfbot mcp server with 80 tools for full user autonomy
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/language-typescript-blue" alt="language">
  <img src="https://img.shields.io/badge/mcp-sdk-orange" alt="mcp">
</p>

---

### installation

**Codex**  
Tell Codex:  
Fetch and follow instructions from https://raw.githubusercontent.com/Microck/discord-selfbot-mcp/refs/heads/master/.codex/INSTALL.md

**OpenCode**  
Tell OpenCode:  
Fetch and follow instructions from https://raw.githubusercontent.com/Microck/discord-selfbot-mcp/refs/heads/master/.opencode/INSTALL.md

---

### manual installation

**one-liner** (recommended for AI terminals):

```bash
npx discord-selfbot-mcp-setup
```

---

### how it works (step by step)

1. **run the setup wizard**
   ```bash
   npx discord-selfbot-mcp-setup
   ```

2. **choose how to provide your token**:
   - `1` = Extract automatically (opens browser, you log in)
   - `2` = Enter token manually (paste your existing token)
   - `3` = Show me how to get a token manually

3. **choose your MCP client**:
   - `1` = Claude Desktop (auto-configures `claude_desktop_config.json`)
   - `2` = Cursor (auto-configures Cursor's MCP settings)
   - `3` = OpenCode / Claude Code CLI (prints config JSON for you to paste)
   - `4` = Generic (saves `mcp.json` to current directory)
   - `5` = Just show me the config (no save)

4. **restart your MCP client** - the discord-selfbot tools are now available

**no .env files needed** - the token is stored directly in your MCP client's config.

---

### getting your token manually

if you prefer not to use the browser extraction:

1. open Discord in your browser (discord.com/app)
2. log in to your account
3. press F12 to open Developer Tools
4. go to the Console tab
5. paste this and press Enter:
   ```js
   (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()
   ```
6. copy the token (without quotes)
7. run `npx discord-selfbot-mcp-setup` and choose option 2 to enter it

---

### manual configuration

if you already have a token, add this to your MCP config:

**claude desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "discord-selfbot": {
      "command": "npx",
      "args": ["discord-selfbot-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_token_here"
      }
    }
  }
}
```

**opencode/claude code** (`.opencode.json` or project config):
```json
{
  "mcpServers": {
    "discord-selfbot": {
      "command": "npx",
      "args": ["discord-selfbot-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_token_here"
      }
    }
  }
}
```

the token is passed via the `env` block in the MCP config - no separate `.env` file required.

---

### captcha handling

when joining servers, discord sometimes requires captcha verification.

**automatic solving** (optional):
```json
{
  "mcpServers": {
    "discord-selfbot": {
      "command": "npx",
      "args": ["discord-selfbot-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_token",
        "CAPTCHA_SERVICE": "capsolver",
        "CAPTCHA_API_KEY": "your_api_key"
      }
    }
  }
}
```

| service | env value | pricing | signup |
|---------|-----------|---------|--------|
| CapSolver | `capsolver` | ~$0.80/1k | [capsolver.com](https://capsolver.com) |
| CapMonster | `capmonster` | ~$0.70/1k | [capmonster.cloud](https://capmonster.cloud) |
| NopeCHA | `nopecha` | 100 free/day | [nopecha.com](https://nopecha.com) |

**browser fallback** (default):

if no captcha service is configured, the MCP automatically:
1. opens a local webpage in your browser
2. shows instructions: "click to open discord invite"
3. you solve the captcha manually in your browser
4. the MCP detects when you've joined and continues

this means **captcha never blocks you** - worst case you solve it yourself in ~10 seconds.

---

### features

**80 tools** across 18 categories.

| category | tools | description |
|----------|-------|-------------|
| **system** | 3 | health, whoami, get_config |
| **guilds** | 8 | list, info, members, nickname, leave, invite, create, delete |
| **channels** | 5 | list, info, create, delete, edit |
| **messages** | 8 | read, send, reply, edit, delete, search, get, forward |
| **reactions** | 4 | react, unreact, get_reactions, remove_all |
| **pins** | 3 | pin, unpin, list_pinned |
| **dms** | 5 | list, read, send, create, close |
| **threads** | 7 | list, create, join, leave, archive, read, send |
| **presence** | 5 | set_status, set_custom, set_activity, clear, get_user |
| **voice** | 5 | join, leave, set_state, get_state, list_members |
| **relationships** | 8 | friends, blocked, pending, request, remove, block, unblock, accept |
| **notifications** | 5 | mentions, mark_read, mark_guild_read, mute_channel, mute_guild |
| **files** | 3 | upload, download, list |
| **events** | 4 | list, get, rsvp, create |
| **profile** | 1 | edit_profile (avatar, bio, username) |
| **interactions** | 4 | trigger_typing, click_button, select_menu, get_components |
| **invites** | 1 | accept_invite (auto browser fallback for captcha) |
| **slash** | 1 | send_slash (execute bot slash commands, waits for response) |

### comparison

| feature | discord-selfbot-mcp | Maol-1997 | codebyyassine | elyxlz |
|---------|---------------------|-----------|---------------|--------|
| read messages | yes | yes | yes | yes |
| send messages | yes | yes | yes | yes |
| list guilds | yes | yes | yes | yes |
| list channels | yes | yes | yes | yes |
| get user info | yes | yes | yes | no |
| search messages | yes | no | no | no |
| create channels | yes | no | yes | no |
| delete channels | yes | no | yes | no |
| edit messages | yes | no | no | no |
| delete messages | yes | no | no | no |
| join voice | yes | no | no | no |
| manage friends | yes | no | no | no |
| manage threads | yes | no | no | no |
| slash commands | yes | no | no | no |
| click buttons | yes | no | no | no |
| select menus | yes | no | no | no |
| setup wizard | yes | no | no | no |
| captcha fallback | yes | no | no | no |
| **total tools** | **80** | **7** | **29** | **4** |

---

### examples

**slash commands** - execute bot commands:
```typescript
send_slash({
  channel_id: "123456789",
  bot_id: "987654321",
  command: "task import",
  args: ["argument1", "argument2"]
})
```

**button clicks** - interact with bot messages:
```typescript
click_button({
  channel_id: "123456789",
  message_id: "987654321",
  button_id: "0,0"  // row 0, col 0 (first button)
})
```

**select menus** - choose dropdown options:
```typescript
select_menu({
  channel_id: "123456789",
  message_id: "987654321", 
  menu_id: "0",
  values: ["option1", "option2"]
})
```

**inspect components** - see all buttons/menus on a message:
```typescript
get_components({
  channel_id: "123456789",
  message_id: "987654321"
})
```

---

### troubleshooting

| problem | solution |
|---------|----------|
| **token invalid** | run `npx discord-selfbot-mcp-setup` to extract a fresh one |
| **rate limited** | reduce `RATE_LIMIT_CONCURRENCY` env var (default: 3) |
| **missing permissions** | ensure account has access to the guild/channel |
| **captcha required** | configure captcha service OR just solve it in the browser popup |
| **mcp not loading** | restart your MCP client after config changes |

---

### project structure

```
src/
├── core/           # configuration, logging, errors, captcha
├── discord/        # discord.js client wrapper
├── mcp/            # mcp server & registry
├── tools/          # 80 tool implementations
│   ├── channels/   # channel management
│   ├── dms/        # direct messages
│   ├── events/     # scheduled events
│   ├── files/      # file upload/download
│   ├── guilds/     # server management
│   ├── interactions/  # buttons, menus, typing
│   ├── invites/    # join servers (with captcha handling)
│   ├── messages/   # send, read, edit, delete, search
│   ├── notifications/ # mentions, mute, mark read
│   ├── presence/   # status, activity
│   ├── profile/    # edit avatar, bio, username
│   ├── relationships/ # friends, blocks
│   ├── slash/      # execute bot slash commands
│   ├── system/     # health, whoami
│   ├── threads/    # thread management
│   └── voice/      # join/leave voice channels
├── index.ts        # entry point
└── setup.ts        # setup wizard
```

---

### license

mit
