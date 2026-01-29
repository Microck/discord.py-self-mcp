#!/usr/bin/env node

const { spawnSync } = require('child_process');

function findPython() {
  const possibleCommands = ['python3', 'python', 'python3.10', 'python3.11', 'python3.12'];
  for (const cmd of possibleCommands) {
    const result = spawnSync(cmd, ['--version'], { stdio: 'ignore' });
    if (result.status === 0) {
      return cmd;
    }
  }
  return null;
}

const pythonCmd = findPython();

if (!pythonCmd) {
  console.warn('⚠️  Warning: Python 3.10+ not found.');
  console.warn('   Please install Python 3.10 or higher to use this package.');
  console.warn('   https://www.python.org/downloads/');
  process.exit(0);
}

const packageCheck = spawnSync(
  pythonCmd,
  ['-c', 'import discord_py_self_mcp'],
  { stdio: 'pipe' }
);

if (packageCheck.status !== 0) {
  console.warn('⚠️  Warning: discord-py-self-mcp Python package not installed.');
  console.warn('');
  console.warn('   To install, run one of the following:');
  console.warn('');
  console.warn('   Using pip:');
  console.warn('     pip install git+https://github.com/Microck/discord.py-self-mcp.git');
  console.warn('');
  console.warn('   Using uv (recommended):');
  console.warn('     uv tool install git+https://github.com/Microck/discord.py-self-mcp.git');
  console.warn('');
  console.warn('   Or install manually:');
  console.warn('     git clone https://github.com/Microck/discord.py-self-mcp.git');
  console.warn('     cd discord.py-self-mcp');
  console.warn('     pip install -e .');
  console.warn('');
}

console.log('✅ discord-selfbot-mcp npm package installed successfully!');
