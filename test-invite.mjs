import { Client } from 'discord.js-selfbot-v13';
import { createCaptchaSolver } from './dist/core/captcha/solver.js';

const token = process.env.DISCORD_TOKEN;
const captchaService = process.env.CAPTCHA_SERVICE || 'none';
const captchaApiKey = process.env.CAPTCHA_API_KEY;

if (!token) {
  console.error('DISCORD_TOKEN not set');
  process.exit(1);
}

console.log(`Captcha service: ${captchaService}`);
console.log(`Captcha API key: ${captchaApiKey ? '***' + captchaApiKey.slice(-4) : 'not set'}`);

const config = {
  captchaService,
  captchaApiKey,
  captchaRetryLimit: 3,
};

const captchaSolver = createCaptchaSolver(config);

const client = new Client({
  checkUpdate: false,
  captchaSolver,
  captchaRetryLimit: 3,
});

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  console.log(`Currently in ${client.guilds.cache.size} guilds`);
  
  console.log('\nAttempting to join invite MWK4rcwk...\n');
  
  try {
    const joined = await client.acceptInvite('MWK4rcwk', {
      bypassOnboarding: true,
      bypassVerify: true,
    });
    
    console.log('SUCCESS! Joined:', joined.name || joined.id);
  } catch (error) {
    console.error('FAILED:', error.message);
  }
  
  client.destroy();
});

client.login(token);
