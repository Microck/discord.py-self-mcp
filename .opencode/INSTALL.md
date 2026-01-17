# install discord-selfbot-mcp

## prerequisites

- [opencode](https://opencode.ai) installed
- node.js installed

## installation steps

### 1. run the setup wizard

run this command in your terminal:

```bash
npx discord-selfbot-mcp-setup
```

### 2. follow the setup instructions

- choose how to provide your discord token (browser extraction or manual entry)
- when asked for the client, choose **opencode** (option 3)
- the wizard will print the configuration json and offer to save it to `mcp.json`

### 3. configure opencode

if the wizard didn't auto-save to your global config, add the following to your `~/.config/opencode/opencode.json` (or your project's `.opencode.json`) file under the `"mcp"` key:

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


### 4. restart opencode

restart your opencode session to load the new tools.

## usage

once installed, you can use any of the 80 discord tools directly:

- `list_guilds()`
- `send_message({ channel_id: "...", content: "..." })`
- `send_slash({ ... })`

## troubleshooting

### token unauthorized (401)

run `npx discord-selfbot-mcp-setup` again to extract a fresh token. discord tokens occasionally expire or are invalidated on password changes.

### captcha required

if a tool triggers a captcha, the mcp will automatically open a local webpage in your browser. follow the instructions there to solve it manually and continue.
