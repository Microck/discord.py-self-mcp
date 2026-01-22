# install discord-selfbot-mcp for codex

## prerequisites

- [codex](https://github.com/google-deepmind/awesome-agentic-coding) installed
- python 3.10+ installed
- `uv` package manager (recommended)

## installation steps

### 1. install the package

```bash
uv tool install git+https://github.com/Microck/discord-selfbot-mcp.git
```

### 2. get your token

run the setup wizard to extract your token:

```bash
uv tool run discord-selfbot-mcp-setup
```

### 3. configure codex

add the following to your codex mcp configuration:

```json
{
  "mcpServers": {
    "discord-selfbot": {
      "command": "uv",
      "args": ["tool", "run", "discord-selfbot-mcp"],
      "env": {
        "DISCORD_TOKEN": "your_discord_token_here"
      }
    }
  }
}
```

### 4. restart codex

restart your session to enable the discord tools.
