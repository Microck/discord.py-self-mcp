<p align="center">
  <img src="https://raw.githubusercontent.com/SAwaris/discord-logo/master/discord-logo-white.png" alt="discord-selfbot-mcp" width="100">
</p>

<h1 align="center">discord-selfbot-mcp</h1>

<p align="center">
  comprehensive discord selfbot mcp server with 60+ tools for full user autonomy
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/language-typescript-blue" alt="language">
  <img src="https://img.shields.io/badge/mcp-sdk-orange" alt="mcp">
</p>

---

### quickstart

automatic setup wizard (extracts token via browser):

```bash
npx discord-selfbot-mcp-setup
```

manual installation:

```bash
npm install -g discord-selfbot-mcp
```

### features

**60 tools** across 14 categories.

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
| **interactions** | 1 | trigger_typing |
| **invites** | 1 | accept_invite |

### usage

run manually (requires token):

```bash
export DISCORD_TOKEN='your_token'
npx discord-selfbot-mcp
```

configure in claude/opencode:

```json
{
  "mcpServers": {
    "discord-selfbot": {
      "command": "npx",
      "args": ["discord-selfbot-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_token"
      }
    }
  }
}
```

### project structure

```bash
src/
├── core/           # configuration, logging, errors
├── discord/        # discord.js client wrapper
├── mcp/            # mcp server & registry
├── tools/          # tool implementations
│   ├── channels/
│   ├── dms/
│   ├── events/
│   ├── files/
│   ├── guilds/
│   ├── interactions/
│   ├── invites/
│   ├── messages/
│   ├── notifications/
│   ├── presence/
│   ├── profile/
│   ├── relationships/
│   ├── system/
│   ├── threads/
│   └── voice/
├── index.ts        # entry point
└── setup.ts        # setup wizard
```

### troubleshooting

| problem | solution |
|---------|----------|
| **token invalid** | run `npx discord-selfbot-mcp-setup` to extract a fresh one |
| **rate limited** | reduce `RATE_LIMIT_CONCURRENCY` env var (default: 3) |
| **missing permissions** | ensure account has access to the guild/channel |
| **verification required** | solve captcha/2fa in browser during setup |

### license

mit
