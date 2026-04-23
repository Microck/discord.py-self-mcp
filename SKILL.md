---
name: discord-cli
description: "Discord operations via CLI with daemon mode for fast execution. Send messages, read channels, list guilds and threads with persistent connection and auto-restart on code changes."
---

# Discord CLI Skill

Perform Discord operations via CLI commands with daemon mode for instant responses.

## Architecture

This skill uses a **client-daemon architecture**:
- **Daemon** (`scripts/daemon.py`): Maintains persistent Discord connection, auto-restarts on code changes
- **Client** (`scripts/dcli.py`): Sends commands to daemon via Unix socket

Benefits:
- **Instant execution**: No WebSocket connection overhead per command
- **Auto-restart**: Daemon automatically restarts when code changes
- **Process management**: Built-in start/stop/restart/status commands

## Prerequisites

- Ensure `.env` file exists in skill root with: `DISCORD_TOKEN=your_token`
- Dependencies must be installed (see Installation section)
- Daemon will auto-start on first command if not already running

## Installation

### First-time Setup (or environment not initialized)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file (add your Discord Token)
echo "DISCORD_TOKEN=your_token_here" > .env
```

### Already Configured (daily use)

If virtual environment and dependencies are already installed, just activate the environment:

```bash
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows
```

## Usage

All commands are executed via local `scripts/dcli.py`:

### Discrawl MCP Tools

This server also exposes dedicated MCP tools to run local `discrawl` commands:

- `run_discrawl` (generic command runner)
- `discrawl_doctor`
- `discrawl_status`
- `discrawl_sync`
- `discrawl_search`
- `discrawl_messages`
- `discrawl_mentions`

By default this MCP prefers a sibling fork build at `../discrawl-self/bin/discrawl`, then falls back to `discrawl` in `PATH`.
Use `DISCRAWL_BIN` if you want to override that:

```bash
DISCRAWL_BIN=/absolute/path/to/discrawl
```

Example MCP payloads:

```json
{"command":"status","config_path":"~/.discrawl/config.toml"}
```

```json
{"guild":"1234567890","since":"2026-03-01T00:00:00Z","full":true,"config_path":"~/.discrawl/config.toml"}
```

### Daemon Management

```bash
# Check status
python3 scripts/dcli.py daemon status

# Start Daemon
python3 scripts/dcli.py daemon start

# Stop Daemon
python3 scripts/dcli.py daemon stop

# Restart Daemon
python3 scripts/dcli.py daemon restart
```

**Note**: The daemon auto-starts when you run any command if it's not already running.

### Discord Commands

#### Send Message
```bash
python3 scripts/dcli.py send-message --channel CHANNEL_ID --content "Hello World"
```

#### Delete Message
```bash
python3 scripts/dcli.py delete-message --channel CHANNEL_ID --message MESSAGE_ID
```

#### Pin Message
```bash
python3 scripts/dcli.py pin-message --channel CHANNEL_ID --message MESSAGE_ID
```

#### Create Thread
```bash
# Create thread from message (in text channel)
python3 scripts/dcli.py create-thread --channel CHANNEL_ID --name "Thread Name" --message MESSAGE_ID

# Create thread in forum channel (with initial content)
python3 scripts/dcli.py create-thread --channel FORUM_CHANNEL_ID --name "Thread Name" --content "Initial post content"
```

#### Read Messages
```bash
python3 scripts/dcli.py read-messages --channel CHANNEL_ID --limit 20

# Read messages after specific time
python3 scripts/dcli.py read-messages --channel CHANNEL_ID --limit 20 --after "4h"
python3 scripts/dcli.py read-messages --channel CHANNEL_ID --after "2024-01-01T00:00:00"
```

#### List Guilds (Servers)
```bash
python3 scripts/dcli.py list-guilds
```

#### List Channels in Guild
```bash
python3 scripts/dcli.py list-channels --guild GUILD_ID
```

**Note**: `list-channels` may not return Forum Channels. To find a Forum Channel ID, use `get-thread-info` on any thread in that forum (see [Working with Forum Channels](#working-with-forum-channels)).

#### List All Threads in Guild
```bash
python3 scripts/dcli.py list-guild-threads --guild GUILD_ID
```

#### List Recent Threads (with activity)
```bash
# List threads active in last 24 hours (default)
python3 scripts/dcli.py list-recent-threads --guild GUILD_ID

# List threads active in last 4 hours
python3 scripts/dcli.py list-recent-threads --guild GUILD_ID --within 4
```

#### Read Recent Threads Messages
```bash
# Read messages from all threads active in last 4 hours
python3 scripts/dcli.py read-recent-threads --guild GUILD_ID --within 4

# Read max 10 messages per thread
python3 scripts/dcli.py read-recent-threads --guild GUILD_ID --within 4 --limit-per-thread 10
```

#### Get User Info
```bash
# Get current user info (supported in daemon mode)
python3 scripts/dcli.py user-info

# Specific user lookup is not currently supported in daemon mode
```

#### List Threads in Channel
```bash
# Active threads only
python3 scripts/dcli.py list-threads --channel CHANNEL_ID

# Include archived threads
python3 scripts/dcli.py list-threads --channel CHANNEL_ID --archived
```

#### Read Thread Messages
```bash
python3 scripts/dcli.py read-thread --thread THREAD_ID --limit 50

# Read messages after specific time
python3 scripts/dcli.py read-thread --thread THREAD_ID --after "4h"
```

#### Get Thread Info
```bash
python3 scripts/dcli.py get-thread-info --thread THREAD_ID
```

**Useful for**: Finding the parent channel (forum) ID of a thread via the `Parent ID` field.

#### Archive/Unarchive Thread
```bash
# Archive thread
python3 scripts/dcli.py archive-thread --thread THREAD_ID

# Unarchive thread
python3 scripts/dcli.py archive-thread --thread THREAD_ID --unarchive
```

#### Join/Leave Thread
```bash
# Join thread
python3 scripts/dcli.py join-thread --thread THREAD_ID

# Leave thread
python3 scripts/dcli.py leave-thread --thread THREAD_ID
```

## Configuration

The skill reads `DISCORD_TOKEN` from `.env` file in the skill root directory.

Create a `.env` file:
```bash
DISCORD_TOKEN=your_discord_token_here
```

### Time Formats

Commands that support `--after` parameter accept the following formats:
- `4h`, `30m`, `1d` - Relative time (hours, minutes, days)
- `2024-01-01T00:00:00` - ISO datetime
- `1704067200` - Unix timestamp

> **Important:** Automating user accounts is against the Discord ToS. Use this at your own risk.

## Notes

- **Daemon Mode**: Uses persistent connection for instant command execution
- **Auto-Restart**: Daemon monitors its own code and restarts automatically when changes are detected
- **Process Management**: Built-in commands to manage the daemon lifecycle
- **Socket Communication**: Client and daemon communicate via a private Unix socket under `$XDG_RUNTIME_DIR/discord-py-self-mcp` or `~/.local/state/discord-py-self-mcp`
- **Rate Limiting**: Respected automatically by the underlying discord.py library

## Working with Forum Channels

Forum Channels are special channels where all conversations happen in threads. To interact with them:

### Finding a Forum Channel ID

Since `list-channels` may not show Forum Channels, use this workaround:

```bash
# 1. List threads to find one in the forum you're looking for
python3 scripts/dcli.py list-guild-threads --guild GUILD_ID

# 2. Get the thread's info to find its parent (forum) channel ID
python3 scripts/dcli.py get-thread-info --thread THREAD_ID
# Output will show "Parent ID: <forum_channel_id>"
```

### Creating Threads in Forum Channels

Forum channels require an initial message when creating a thread:

```bash
python3 scripts/dcli.py create-thread \
  --channel FORUM_CHANNEL_ID \
  --name "Thread Title" \
  --content "This is the initial post content"
```

## Troubleshooting

**Daemon not responding?**
```bash
# Check if daemon is running
python3 scripts/dcli.py daemon status

# Restart daemon
python3 scripts/dcli.py daemon restart
```

**Socket errors?**
```bash
# Clean up and restart
python3 scripts/dcli.py daemon stop
python3 scripts/dcli.py daemon start
```

**Python not found?**
Ensure Python 3.10+ is installed and available in PATH.

## Related

- [Main Repository](https://github.com/Microck/discord.py-self-mcp)
- [MCP Documentation](./README.md)
- [discord.py-self](https://github.com/dolfies/discord.py-self) - Underlying library
