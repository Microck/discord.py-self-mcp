<p align="center">
  <img src="./logo.png" alt="discord-selfbot-mcp" width="100">
</p>

# discord-selfbot-mcp

discord-selfbot-mcp is a comprehensive model context protocol (mcp) server that gives your ai agents full autonomy over a discord user account. with 80 specialized tools, it enables agents to communicate, manage communities, and interact with other bots just like a human user.

## how it works

it starts with a simple setup. instead of hunting for tokens and managing complex `.env` files, you run a single command that guides you through the process. it can even open a browser to extract your token automatically.

once configured, your ai agent gains access to 18 categories of tools. it doesn't just read and send messages; it can join voice channels, manage relationships, interact with buttons and menus, execute slash commands, and even handle captchas through a smart browser fallback system.

the server is designed for reliability. if discord challenges the agent with a captcha while joining a server, the mcp automatically opens a local window for you to solve it manually, ensuring your agent's workflow is never permanently blocked.

## installation

**note:** installation is streamlined for ai-native environments.

### codex

tell codex:

```
fetch and follow instructions from https://raw.githubusercontent.com/Microck/discord-selfbot-mcp/refs/heads/master/.codex/INSTALL.md
```

### opencode

tell opencode:

```
fetch and follow instructions from https://raw.githubusercontent.com/Microck/discord-selfbot-mcp/refs/heads/master/.opencode/INSTALL.md
```

### manual (one-liner)

for other terminals, run the setup wizard directly:

```bash
npx discord-selfbot-mcp-setup
```

## the basic workflow

1. **setup** - run the wizard to extract or provide your discord token.
2. **configure** - the wizard auto-configures claude desktop, cursor, or provides the json for opencode/codex.
3. **connect** - restart your mcp client.
4. **automate** - your agent can now use all 80 tools across any discord server or dm.

## what's inside

### tools library (80 tools)

**communication**
- **messages** - read, send, reply, edit, delete, search, forward
- **dms** - list, read, send, create, close
- **threads** - list, create, join, leave, archive, read, send
- **notifications** - mentions, mark read, mute channels/guilds

**interactions**
- **interactions** - trigger typing, click buttons, select menus, get components
- **slash** - execute bot slash commands and wait for responses
- **reactions** - react, unreact, get reactions, remove all
- **invites** - join servers with auto browser fallback for captchas

**management**
- **guilds** - list, info, members, nickname, leave, create, delete
- **channels** - list, info, create, delete, edit
- **pins** - pin, unpin, list pinned
- **events** - list, get, rsvp, create

**account & presence**
- **profile** - edit avatar, bio, and username
- **presence** - set status, custom status, activity, and get user presence
- **relationships** - manage friends, blocks, and pending requests
- **voice** - join/leave voice channels, manage voice state

**system & files**
- **files** - upload, download, and list attachments
- **system** - health check, whoami, and get current config

## philosophy

- **full autonomy** - if a user can do it, the agent should be able to do it.
- **no-block design** - browser fallback for captchas ensures continuous operation.
- **zero configuration** - setup wizards over manual `.env` management.
- **agent-first** - tool schemas optimized for llm understanding and reliable execution.

## license

mit license - see license file for details

## support

- **issues**: https://github.com/Microck/discord-selfbot-mcp/issues
