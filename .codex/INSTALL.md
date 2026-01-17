# install discord-selfbot-mcp for codex

## prerequisites

- [codex](https://github.com/google-deepmind/awesome-agentic-coding) installed
- node.js installed

## installation steps

### 1. run the setup wizard

run this command in your terminal:

```bash
npx discord-selfbot-mcp-setup
```

### 2. follow the setup instructions

- choose how to provide your discord token
- when asked for the client, choose **generic** or **just show me the config**
- copy the token or the json config

### 3. configure codex

add the following to your `~/.config/opencode/opencode.json` file under the `"mcp"` key:

```json
"discord-selfbot": {
  "type": "local",
  "command": [
    "npx",
    "discord-selfbot-mcp"
  ],
  "enabled": true,
  "environment": {
    "DISCORD_TOKEN": "your_discord_token_here"
  }
}
```


### 4. restart codex

restart your session to enable the discord tools.
