# Discord Selfbot MCP

The most comprehensive Discord Selfbot MCP (Model Context Protocol) server. 50+ tools for full Discord user functionality.

**WARNING: This uses a selfbot which violates Discord's Terms of Service. Use at your own risk. Your account may be terminated.**

## Features

### 55 Tools Across 12 Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **System** | 3 | health, whoami, get_config |
| **Guilds** | 6 | list, info, members, nickname, leave, invite |
| **Channels** | 5 | list, info, create, delete, edit |
| **Messages** | 8 | read, send, reply, edit, delete, search, get, forward |
| **Reactions** | 4 | react, unreact, get_reactions, remove_all |
| **Pins** | 3 | pin, unpin, list_pinned |
| **DMs** | 5 | list, read, send, create, close |
| **Threads** | 7 | list, create, join, leave, archive, read, send |
| **Presence** | 5 | set_status, set_custom, set_activity, clear, get_user |
| **Voice** | 5 | join, leave, set_state, get_state, list_members |
| **Relationships** | 8 | friends, blocked, pending, send_request, remove, block, unblock, accept |
| **Notifications** | 5 | get_mentions, mark_read, mark_guild_read, mute_channel, mute_guild |
| **Files** | 3 | upload, download, list_attachments |
| **Events** | 4 | list, get, rsvp, create |

## Quick Start (Auto Setup)

We provide a setup wizard that automatically extracts your token from Discord web login:

```bash
npx discord-selfbot-mcp-setup
```

This will:
1. Open a browser window
2. Let you log in to Discord
3. Automatically grab your token
4. Configure Claude Desktop or Cursor for you

## Manual Installation

```bash
npm install -g discord-selfbot-mcp
```

Or use directly with npx:
```bash
npx discord-selfbot-mcp
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | Yes | - | Your Discord user token |
| `DANGER_MODE` | No | false | Enable dangerous operations (friend/block) |
| `LOG_LEVEL` | No | info | debug, info, warn, error |
| `ALLOW_DMS` | No | true | Enable DM features |
| `ALLOW_RELATIONSHIPS` | No | false | Enable friend/block features |
| `ALLOW_VOICE` | No | true | Enable voice features |
| `REDACT_CONTENT` | No | false | Redact message content in logs |
| `ALLOWED_GUILDS` | No | - | Comma-separated guild IDs whitelist |
| `RATE_LIMIT_CONCURRENCY` | No | 3 | Max concurrent Discord API calls |

### MCP Client Configuration

#### Claude Desktop

Add to `claude_desktop_config.json`:

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

#### Cursor / Other MCP Clients

```json
{
  "discord-selfbot": {
    "command": "npx",
    "args": ["discord-selfbot-mcp"],
    "env": {
      "DISCORD_TOKEN": "your_token_here"
    }
  }
}
```

## Getting Your Discord Token

1. Open Discord in your browser (discord.com/app)
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Paste and run:
```javascript
(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
```
5. Copy the token (without quotes)

**Never share your token with anyone.**

## Usage Examples

### Read Messages
```
Read the last 20 messages from channel 123456789
```

### Send Message
```
Send "Hello world!" to channel 123456789
```

### Search Messages
```
Search for messages containing "important" in guild 123456789
```

### Set Status
```
Set my status to "do not disturb"
```

### Join Voice
```
Join voice channel 123456789
```

## Safety Features

- **Rate Limiting**: Built-in queue with configurable concurrency
- **Feature Gating**: DMs, relationships, voice can be disabled
- **Danger Mode**: Extra confirmation for destructive operations
- **Guild Whitelist**: Restrict operations to specific servers
- **Error Normalization**: Consistent error responses

## Project Structure

```
src/
  index.ts              # Entry point
  core/
    config.ts           # Configuration
    logger.ts           # Logging
    errors/             # Error handling
    rateLimit/          # Rate limiting
    resolvers/          # ID parsing
    formatting/         # DTO formatting
  discord/
    client.ts           # Discord client wrapper
  mcp/
    server.ts           # MCP server
    registry.ts         # Tool registry
  tools/
    system/             # health, whoami
    guilds/             # Guild operations
    channels/           # Channel operations
    messages/           # Message operations
    dms/                # DM operations
    threads/            # Thread operations
    presence/           # Status/activity
    voice/              # Voice channels
    relationships/      # Friends/blocks
    notifications/      # Mentions/mute
    files/              # File upload/download
    events/             # Scheduled events
```

## Development

```bash
git clone https://github.com/yourname/discord-selfbot-mcp
cd discord-selfbot-mcp
npm install
npm run dev
```

### Build

```bash
npm run build
```

### Type Check

```bash
npm run typecheck
```

## License

MIT

## Disclaimer

This software is provided for educational purposes only. Using selfbots violates Discord's Terms of Service and may result in account termination. The authors are not responsible for any consequences of using this software.
