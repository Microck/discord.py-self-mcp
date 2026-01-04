import { chromium } from 'playwright';
import { join } from 'path';
import { homedir } from 'os';
import { mkdir } from 'fs/promises';

const token = process.env.DISCORD_TOKEN;
if (!token) {
  console.error('DISCORD_TOKEN not set');
  process.exit(1);
}

const USER_DATA_DIR = join(homedir(), '.discord-selfbot-mcp', 'browser-data');
const STORAGE_STATE_PATH = join(USER_DATA_DIR, 'storage-state.json');

async function test() {
  await mkdir(USER_DATA_DIR, { recursive: true });
  
  console.log('Launching browser...');
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-default-browser-check',
    ],
  });

  let context;
  try {
    context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      storageState: STORAGE_STATE_PATH,
    });
    console.log('Loaded saved session');
  } catch {
    context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    });
    console.log('No saved session, starting fresh');
  }

  const page = await context.newPage();

  await page.addInitScript((discordToken) => {
    const currentToken = localStorage.getItem('token');
    if (!currentToken || currentToken === 'null' || currentToken === '""') {
      localStorage.setItem('token', JSON.stringify(discordToken));
    }
  }, token);

  console.log('Navigating to invite...');
  console.log('>>> SOLVE THE CAPTCHA IN THE BROWSER WINDOW <<<');
  await page.goto('https://discord.com/invite/MWK4rcwk', { waitUntil: 'domcontentloaded' });

  console.log('Waiting 120 seconds for you to solve captcha and join...');
  await new Promise(resolve => setTimeout(resolve, 120000));

  console.log('Saving session...');
  await context.storageState({ path: STORAGE_STATE_PATH });
  
  await browser.close();
  console.log('Done');
}

test().catch(console.error);
