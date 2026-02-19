#!/usr/bin/env node

const { chromium } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');
const readline = require('readline');

const DISCORD_URL = 'https://discord.com/login';
const SERVER_KEY = 'discord-py-self';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(prompt) {
  return new Promise(resolve => rl.question(prompt, resolve));
}

function fileExists(p) {
  try {
    fs.accessSync(p, fs.constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function ensureDirForFile(filePath) {
  const dir = path.dirname(filePath);
  fs.mkdirSync(dir, { recursive: true });
}

function readJsonFile(filePath) {
  const raw = fs.readFileSync(filePath, 'utf-8');
  return JSON.parse(raw);
}

function backupFile(filePath) {
  if (!fileExists(filePath)) return null;
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  const backupPath = `${filePath}.bak.${stamp}`;
  fs.copyFileSync(filePath, backupPath);
  return backupPath;
}

function writeJsonFile(filePath, data) {
  ensureDirForFile(filePath);
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n');
}

function buildGenericMcpServersEntry(token) {
  return {
    command: 'discord-selfbot-mcp',
    env: {
      DISCORD_TOKEN: token
    }
  };
}

function buildOpenCodeMcpEntry(token) {
  return {
    command: ['discord-selfbot-mcp'],
    enabled: true,
    type: 'local',
    environment: {
      DISCORD_TOKEN: token
    }
  };
}

function upsertMcpServerConfig(existing, token, mode) {
  const root = (existing && typeof existing === 'object') ? existing : {};
  if (mode === 'opencode-mcp') {
    if (!root.mcp || typeof root.mcp !== 'object') root.mcp = {};
    root.mcp[SERVER_KEY] = buildOpenCodeMcpEntry(token);
    return root;
  }

  if (!root.mcpServers || typeof root.mcpServers !== 'object') root.mcpServers = {};
  root.mcpServers[SERVER_KEY] = buildGenericMcpServersEntry(token);
  return root;
}

function detectClientConfigs() {
  const home = os.homedir();
  const results = [];

  // OpenCode
  const openCodePath = path.join(home, '.config', 'opencode', 'opencode.json');
  if (fileExists(openCodePath)) {
    results.push({ label: 'OpenCode', filePath: openCodePath, mode: 'opencode-auto' });
  }

  // Claude Desktop (and some Claude Code installs that reuse the same config)
  let claudePath = null;
  if (process.platform === 'darwin') {
    claudePath = path.join(home, 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
  } else if (process.platform === 'win32') {
    const appData = process.env.APPDATA;
    if (appData) claudePath = path.join(appData, 'Claude', 'claude_desktop_config.json');
  } else {
    claudePath = path.join(home, '.config', 'Claude', 'claude_desktop_config.json');
  }
  if (claudePath && fileExists(claudePath)) {
    results.push({ label: 'Claude Desktop', filePath: claudePath, mode: 'mcpServers' });
  }

  // Codex CLI (best-effort common paths)
  const codexCandidates = [
    path.join(home, '.config', 'codex', 'config.json'),
    path.join(home, '.config', 'codex', 'mcp.json'),
    path.join(home, '.codex', 'config.json'),
    path.join(home, '.codex', 'mcp.json')
  ];
  for (const p of codexCandidates) {
    if (fileExists(p)) {
      results.push({ label: 'Codex', filePath: p, mode: 'mcpServers' });
      break;
    }
  }

  // Gemini CLI (best-effort common paths)
  const geminiCandidates = [
    path.join(home, '.config', 'gemini', 'config.json'),
    path.join(home, '.config', 'gemini', 'mcp.json'),
    path.join(home, '.config', 'gemini-cli', 'config.json'),
    path.join(home, '.gemini', 'config.json'),
    path.join(home, '.gemini', 'mcp.json')
  ];
  for (const p of geminiCandidates) {
    if (fileExists(p)) {
      results.push({ label: 'Gemini CLI', filePath: p, mode: 'mcpServers' });
      break;
    }
  }

  return results;
}

async function applyConfigToFile(filePath, token, mode) {
  let existing = {};
  if (fileExists(filePath)) {
    existing = readJsonFile(filePath);
  }

  const actualMode = (mode === 'opencode-auto')
    ? ((existing && typeof existing === 'object' && existing.mcp && typeof existing.mcp === 'object') ? 'opencode-mcp' : 'mcpServers')
    : mode;

  const updated = upsertMcpServerConfig(existing, token, actualMode);
  const backupPath = backupFile(filePath);
  writeJsonFile(filePath, updated);
  return { backupPath, actualMode };
}

async function getTokenFromBrowser() {
  console.log('Opening browser...');

  const browser = await chromium.launch({
    headless: false,
    args: ['--disable-blink-features=AutomationControlled']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });

  const page = await context.newPage();
  await page.goto(DISCORD_URL);

  console.log('Please log in to Discord in the opened browser window.');
  console.log('The script will automatically detect your token once you are logged in.');

  let token = null;
  while (!token) {
    try {
      token = await page.evaluate(`
        (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()
      `);
      if (token) {
        break;
      }
    } catch (e) {
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  console.log(`Token found: ${token.substring(0, 20)}...${token.substring(token.length - 5)}`);
  await browser.close();
  return token;
}

function generateConfig(token) {
  return {
    mcpServers: {
      [SERVER_KEY]: buildGenericMcpServersEntry(token)
    }
  };
}

async function main() {
  // Non-interactive mode via environment variables
  if (process.env.DISCORD_TOKEN) {
    const token = process.env.DISCORD_TOKEN;
    const targetPath = process.env.MCP_CONFIG_PATH || path.join(os.homedir(), '.config', 'mcp.json'); // Default to ~/.config/mcp.json if not specified
    
    console.log('Running in non-interactive mode (DISCORD_TOKEN set).');
    console.log('Generating configuration...');
    
    // Auto-detect if path points to OpenCode config
    const isOpenCode = targetPath.endsWith('opencode.json');
    const mode = isOpenCode ? 'opencode-auto' : 'mcpServers';

    try {
      const { backupPath, actualMode } = await applyConfigToFile(targetPath, token, mode);
      console.log(`\nWrote config to: ${targetPath}`);
      if (backupPath) console.log(`Backup created: ${backupPath}`);
      if (actualMode === 'opencode-mcp') console.log('Configured using OpenCode `mcp` shape.');
      else console.log('Configured using `mcpServers` shape.');
      process.exit(0);
    } catch (e) {
      console.error(`\nFailed to write config: ${e.message}`);
      process.exit(1);
    }
  }

  console.log('=== Discord Selfbot MCP Setup ===');
  console.log('1. Extract token automatically (browser)');
  console.log('2. Enter token manually');

  const choice = await question('Choice (1/2): ');

  let token = null;
  if (choice === '1') {
    token = await getTokenFromBrowser();
  } else {
    token = await question('Enter your Discord token: ');
  }

  if (!token) {
    console.log('No token provided.');
    rl.close();
    process.exit(1);
  }

  console.log('\nGenerated MCP Configuration:');
  console.log(JSON.stringify(generateConfig(token), null, 2));

  const detected = detectClientConfigs();
  const options = [...detected];
  options.push({ label: 'Local mcp.json (current dir)', filePath: path.join(process.cwd(), 'mcp.json'), mode: 'mcpServers' });

  console.log('\nWhere should I write this configuration?');
  for (let i = 0; i < options.length; i++) {
    console.log(`${i + 1}. ${options[i].label} -> ${options[i].filePath}`);
  }
  console.log(`${options.length + 1}. Enter a custom path`);
  console.log(`${options.length + 2}. Skip (do not write anything)`);

  const selectedRaw = await question(`Choice (1-${options.length + 2}): `);
  const selected = Number(selectedRaw);

  if (Number.isFinite(selected) && selected >= 1 && selected <= options.length) {
    const opt = options[selected - 1];
    try {
      const { backupPath, actualMode } = await applyConfigToFile(opt.filePath, token, opt.mode);
      console.log(`\nWrote config to: ${opt.filePath}`);
      if (backupPath) console.log(`Backup created: ${backupPath}`);
      if (actualMode === 'opencode-mcp') console.log('Configured using OpenCode `mcp` shape.');
      else console.log('Configured using `mcpServers` shape.');
    } catch (e) {
      console.error(`\nFailed to write config: ${e.message}`);
    }
  } else if (Number.isFinite(selected) && selected === options.length + 1) {
    const customPath = (await question('Enter config file path: ')).trim();
    if (customPath) {
      try {
        const { backupPath } = await applyConfigToFile(customPath, token, 'mcpServers');
        console.log(`\nWrote config to: ${customPath}`);
        if (backupPath) console.log(`Backup created: ${backupPath}`);
      } catch (e) {
        console.error(`\nFailed to write config: ${e.message}`);
      }
    }
  } else {
    console.log('\nSkipped writing config.');
  }

  rl.close();
}

main().catch(err => {
  console.error('Error:', err.message);
  rl.close();
  process.exit(1);
});
