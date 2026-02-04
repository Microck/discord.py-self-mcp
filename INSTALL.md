# Installation

## For Humans

Paste this into your LLM agent session:

```
Install and configure discord-selfbot-mcp by following the instructions here:
https://raw.githubusercontent.com/Microck/discord.py-self-mcp/refs/heads/master/INSTALL.md
```

### Prerequisites

- Python 3.10+
- Node.js 18+ (only if you want the npm wrapper)
- Optional: `uv` (recommended) or `pip`
- Voice support (Linux only): `libffi-dev` (or `libffi-devel`), `python3-dev`

### Option 1: npm wrapper (recommended)

```bash
npm install -g discord-selfbot-mcp
discord-selfbot-mcp-setup
```

The setup wizard can auto-detect common MCP client config files (when present) and write the server entry for you (it creates a backup before editing).

This installs a small Node.js wrapper that launches the underlying Python MCP server.

### Option 2: Python only (uv/pip)

```bash
# uv (recommended)
uv tool install git+https://github.com/Microck/discord.py-self-mcp.git

# or pip
pip install git+https://github.com/Microck/discord.py-self-mcp.git
```

Run the setup wizard:

```bash
discord-py-self-mcp-setup
# or
python3 -m discord_py_self_mcp.setup
```

The setup wizard can auto-detect common MCP client config files (when present) and write the server entry for you (it creates a backup before editing).

## Configure Your MCP Client

This server uses `stdio` transport (your MCP client runs it as a local process). Provide your token via the MCP server configuration environment.

If you want templates, see:

- `mcp.example.json` (npm wrapper)
- `mcp.python.example.json` (python console script)
- `.env.example`

### Example (stdio, npm wrapper)

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

### Example (stdio, python console script)

```json
{
  "mcpServers": {
    "discord-py-self": {
      "command": "discord-py-self-mcp",
      "env": {
        "DISCORD_TOKEN": "${DISCORD_TOKEN}"
      }
    }
  }
}
```

If your MCP client does not expand `${DISCORD_TOKEN}`, replace it with the literal token value.

## Verify

Restart your MCP client and verify the server connects.

A good smoke test is calling:

- `list_guilds`

## Notes

- Automating user accounts violates Discord ToS. Use at your own risk.
- Do not commit tokens. This repo ignores `mcp.json` and `.env` by default.

---

## For LLM Agents

Follow these steps when you are assisting a user.

### Step 0: Check prerequisites

```bash
python --version
node --version
npm --version
uv --version
```

### Step 1: Choose an install method

- Prefer npm wrapper if the user already has Node.js 18+
- Otherwise use Python (uv if available, pip if not)

### Step 2: Install

**npm**

```bash
npm install -g discord-selfbot-mcp
```

**python**

```bash
uv tool install git+https://github.com/Microck/discord.py-self-mcp.git
# or
pip install git+https://github.com/Microck/discord.py-self-mcp.git
```

### Step 3: Run the setup wizard

```bash
discord-selfbot-mcp-setup
# or
python3 -m discord_py_self_mcp.setup
```

### Step 4: Configure the user's MCP client

Tell the user to paste the generated MCP config into their MCP client settings and set `DISCORD_TOKEN` in the server `env`.

### Step 5: Verify

Have the user restart their MCP client and run `list_guilds`.

---

## Troubleshooting

- Playwright issues: `playwright install chromium`
- Token invalid: extract a fresh token (Discord rotates tokens after password change)
- Voice issues on Linux: install `libffi-dev` and `python3-dev`
- Captcha solver setup: `python -m camoufox fetch` and set `GROQ_API_KEY` in the MCP server `env`

### Python Module Not Found

If you see `ModuleNotFoundError: No module named 'mcp'`:

1. **If using npm wrapper**:
   - The npm wrapper automatically finds the Python version with required packages
   - If it fails, it will show which Python versions were checked
   - Example error: `Error: mcp module not found in python3.14`
   - This means python3.14 doesn't have mcp, but python3.10 does
   - Solution: Install npm package, which will detect the correct Python

2. **If using Python directly**:
   ```bash
   # Install with pip (system-wide)
   pip install git+https://github.com/Microck/discord.py-self-mcp.git

   # Or with --user flag (user install)
   pip install --user git+https://github.com/Microck/discord.py-self-mcp.git
   ```

3. **If you see "externally-managed-environment" error**:
   - This happens on systems with managed Python (Ubuntu/Debian with Homebrew)
   - Solution: Use npm wrapper instead: `npm install -g discord-selfbot-mcp`
   - Or create a virtual environment:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     pip install git+https://github.com/Microck/discord.py-self-mcp.git
     ```

4. **Verify installation**:
   ```bash
   # Check if discord_py_self_mcp is installed
   python3 -c "import discord_py_self_mcp; print('OK')"

   # Check if mcp is installed
   python3 -c "import mcp; print('OK')"
   ```
