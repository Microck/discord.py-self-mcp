# install discord-selfbot-mcp

## prerequisites

- [opencode](https://opencode.ai) installed
- python 3.10+ installed
- `uv` package manager (recommended)

## installation steps

### 1. install the package

```bash
uv tool install git+https://github.com/Microck/discord-selfbot-mcp.git
```

### 2. run the setup wizard

run this command to generate your config and get your token:

```bash
uv tool run discord-selfbot-mcp-setup
# or if running from source
python3 discord_selfbot_mcp/setup.py
```

- choose option 1 to extract token via browser (requires playwright)
- or option 2 to paste it manually

### 3. configure opencode

add the following to your `~/.config/opencode/opencode.json` (or your project's `.opencode.json`) under the `mcp` object:

```json
{
  "mcp": {
    "discord-selfbot": {
      "command": ["uv", "tool", "run", "discord-selfbot-mcp"],
      "enabled": true,
      "type": "local",
      "environment": {
        "DISCORD_TOKEN": "your_discord_token_here"
      }
    }
  }
}
```

### 4. restart opencode

restart your opencode session to load the new tools.

## usage

once installed, you can use the available tools:

- `list_guilds()`
- `send_message({ channel_id: "...", content: "..." })`
- `read_messages({ channel_id: "..." })`
