#!/usr/bin/env node
import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import * as readline from 'readline';

const DISCORD_URL = 'https://discord.com/login';
const CONFIG_PATHS = {
  claude: getClaudeConfigPath(),
  cursor: getCursorConfigPath(),
  generic: path.join(process.cwd(), 'mcp-config.json'),
};

function getClaudeConfigPath(): string {
  const home = process.env.HOME || process.env.USERPROFILE || '';
  if (process.platform === 'win32') {
    return path.join(process.env.APPDATA || '', 'Claude', 'claude_desktop_config.json');
  } else if (process.platform === 'darwin') {
    return path.join(home, 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json');
  }
  return path.join(home, '.config', 'claude', 'claude_desktop_config.json');
}

function getCursorConfigPath(): string {
  const home = process.env.HOME || process.env.USERPROFILE || '';
  if (process.platform === 'win32') {
    return path.join(process.env.APPDATA || '', 'Cursor', 'User', 'globalStorage', 'mcp.json');
  } else if (process.platform === 'darwin') {
    return path.join(home, 'Library', 'Application Support', 'Cursor', 'User', 'globalStorage', 'mcp.json');
  }
  return path.join(home, '.config', 'cursor', 'mcp.json');
}

function prompt(question: string): Promise<string> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function extractToken(page: { evaluate: (fn: () => string | null) => Promise<string | null> }): Promise<string | null> {
  try {
    const token = await page.evaluate(() => {
      const iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      document.body.appendChild(iframe);
      
      const localStorage = iframe.contentWindow?.localStorage;
      if (!localStorage) return null;
      
      const token = localStorage.getItem('token');
      if (token) {
        document.body.removeChild(iframe);
        return token.replace(/"/g, '');
      }
      
      document.body.removeChild(iframe);
      return null;
    });
    
    if (token) return token;
    
    const tokenViaWebpack = await page.evaluate(() => {
      try {
        const wp = (window as unknown as { webpackChunkdiscord_app?: unknown[] }).webpackChunkdiscord_app;
        if (!wp) return null;
        
        let token: string | null = null;
        wp.push([
          ['__extract__'],
          {},
          (require: (id: string) => { c: Record<string, { exports?: { default?: { getToken?: () => string } } }> }) => {
            const cache = require('').c;
            for (const id in cache) {
              const mod = cache[id]?.exports?.default;
              if (mod?.getToken) {
                token = mod.getToken();
                break;
              }
            }
          },
        ]);
        return token;
      } catch {
        return null;
      }
    });
    
    return tokenViaWebpack;
  } catch {
    return null;
  }
}

function generateMcpConfig(token: string): object {
  return {
    mcpServers: {
      'discord-selfbot': {
        command: 'npx',
        args: ['discord-selfbot-mcp'],
        env: {
          DISCORD_TOKEN: token,
        },
      },
    },
  };
}

function mergeConfig(existingPath: string, newConfig: { mcpServers: object }): object {
  let existing: { mcpServers?: object } = {};
  
  if (fs.existsSync(existingPath)) {
    try {
      existing = JSON.parse(fs.readFileSync(existingPath, 'utf-8'));
    } catch {
      existing = {};
    }
  }
  
  return {
    ...existing,
    mcpServers: {
      ...(existing.mcpServers || {}),
      ...newConfig.mcpServers,
    },
  };
}

function saveConfig(configPath: string, config: object): void {
  const dir = path.dirname(configPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
}

function isValidToken(token: string): boolean {
  if (!token || token.length < 50 || token.includes(' ')) {
    return false;
  }
  return true;
}

async function configureWithToken(token: string, choice: string): Promise<void> {
  const mcpConfig = generateMcpConfig(token);
  let configPath: string;

  if (choice === '3') {
    console.log('\n=== OpenCode / Claude Code Configuration ===');
    console.log('For CLI tools, add this to your project config or settings:\n');
    console.log(JSON.stringify(mcpConfig, null, 2));
    
    console.log('\nOr set as environment variable for manual execution:');
    if (process.platform === 'win32') {
      console.log(`set DISCORD_TOKEN=${token}`);
    } else {
      console.log(`export DISCORD_TOKEN='${token}'`);
    }
    
    const save = await prompt('\nSave to mcp.json in current directory anyway? (y/n): ');
    if (save.toLowerCase() !== 'y') {
      console.log('\nDone! Copy the JSON above to your MCP config.');
      return;
    }
    configPath = path.join(process.cwd(), 'mcp.json');
  } else {
    switch (choice) {
      case '1':
        configPath = CONFIG_PATHS.claude;
        break;
      case '2':
        configPath = CONFIG_PATHS.cursor;
        break;
      default:
        configPath = CONFIG_PATHS.generic;
    }
  }
  
  const finalConfig = mergeConfig(configPath, mcpConfig as { mcpServers: object });
  saveConfig(configPath, finalConfig);
  
  console.log(`\nConfiguration saved to: ${configPath}`);
  console.log('\nSetup complete! Restart your MCP client to use discord-selfbot.');
  
  if (choice === '1') {
    console.log('\nFor Claude Desktop:');
    console.log('1. Quit Claude Desktop completely');
    console.log('2. Reopen Claude Desktop');
    console.log('3. The discord-selfbot MCP should now be available');
  }
}

async function main() {
  console.log('\n=== Discord Selfbot MCP Setup ===\n');
  
  console.log('How do you want to provide your Discord token?\n');
  console.log('1. Extract automatically (opens browser, you log in)');
  console.log('2. Enter token manually (paste your existing token)');
  console.log('3. Show me how to get a token manually\n');
  
  const method = await prompt('Choice (1-3): ');
  
  if (method === '3') {
    console.log('\n=== How to get your Discord token manually ===\n');
    console.log('1. Open Discord in your browser (discord.com/app)');
    console.log('2. Log in to your account');
    console.log('3. Press F12 to open Developer Tools');
    console.log('4. Go to the Console tab');
    console.log('5. Paste this code and press Enter:\n');
    console.log('   (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()');
    console.log('\n6. Copy the token (without quotes)');
    console.log('7. Run this setup again and choose option 2\n');
    console.log('WARNING: Never share your token with anyone!');
    console.log('Anyone with your token has full access to your account.\n');
    return;
  }
  
  console.log('\nWARNING: Using selfbots violates Discord ToS.');
  console.log('Your account may be terminated.\n');
  
  const proceed = await prompt('Continue? (y/n): ');
  if (proceed.toLowerCase() !== 'y') {
    console.log('Aborted.');
    process.exit(0);
  }
  
  console.log('\nSelect MCP client to configure:');
  console.log('1. Claude Desktop');
  console.log('2. Cursor');
  console.log('3. OpenCode / Claude Code (CLI)');
  console.log('4. Generic (save to current directory)');
  console.log('5. Just show me the config (no save)\n');
  
  const choice = await prompt('Choice (1-5): ');
  
  let token: string | null = null;
  
  if (method === '2') {
    console.log('\nPaste your Discord token below.');
    console.log('(It will be hidden for security)\n');
    
    token = await prompt('Token: ');
    
    if (!isValidToken(token)) {
      console.log('\nInvalid token format. Token should be at least 50 characters.');
      console.log('Run the setup again and choose option 3 to learn how to get your token.');
      process.exit(1);
    }
    
    console.log('\nToken accepted!');
    console.log(`Token: ${token.slice(0, 20)}...${token.slice(-10)}\n`);
  } else {
    console.log('\nLaunching browser...');
    console.log('Please log in to Discord in the browser window.\n');
    
    const browser = await chromium.launch({
      headless: false,
      args: ['--disable-blink-features=AutomationControlled'],
    });
    
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
    
    const page = await context.newPage();
    await page.goto(DISCORD_URL);
    
    console.log('Waiting for you to log in...');
    console.log('(The script will detect when you reach the Discord app)\n');
    
    const maxWaitTime = 5 * 60 * 1000;
    const startTime = Date.now();
    
    while (!token && Date.now() - startTime < maxWaitTime) {
      try {
        token = await extractToken(page);
        
        if (!token) {
          await page.waitForTimeout(1000);
        }
      } catch {
        await page.waitForTimeout(1000);
      }
    }
    
    if (token) {
      console.log('\nToken detected!');
      console.log('If Discord is asking for verification (email code, captcha, etc.), please complete it now.');
      console.log('The browser will stay open until you are done.\n');
      await prompt('Press Enter here when you are fully logged in and see the Discord chat... ');
    }
    
    await browser.close();
    
    if (!token) {
      console.log('\nFailed to extract token automatically.');
      console.log('Run this setup again and choose option 2 to enter your token manually,');
      console.log('or option 3 to learn how to get your token.\n');
      process.exit(1);
    }
    
    console.log('\nToken extracted successfully!');
    console.log(`Token: ${token.slice(0, 20)}...${token.slice(-10)}\n`);
  }
  
  if (choice === '5') {
    console.log('=== MCP Configuration ===\n');
    console.log(JSON.stringify(generateMcpConfig(token), null, 2));
    console.log('\nCopy this JSON to your MCP client config file.');
    console.log('\nFull token (for manual use):');
    console.log(token);
    return;
  }
  
  await configureWithToken(token, choice);
}

main().catch((err) => {
  console.error('Setup failed:', err.message);
  process.exit(1);
});
