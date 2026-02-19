#!/usr/bin/env node

const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function readPackageVersion() {
  try {
    const pkgPath = path.join(__dirname, 'package.json');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    return pkg.version || null;
  } catch {
    return null;
  }
}

function checkPythonVersion(cmd) {
  try {
    const result = spawnSync(cmd, ['--version'], { stdio: ['ignore', 'pipe', 'pipe'], encoding: 'utf8' });
    const output = result.stdout || result.stderr || '';
    if (result.status === 0) {
      const version = output.match(/Python (\d+\.\d+)/)?.[1];
      if (version) {
        const [major, minor] = version.split('.').map(Number);
        if (major > 3 || (major === 3 && minor >= 10)) {
          return true;
        }
      }
    }
  } catch (e) {
  }
  return false;
}

function checkPythonPackage(pythonCmd, packageName) {
  try {
    const result = spawnSync(
      pythonCmd,
      ['-c', `import ${packageName}; print('OK')`],
      { stdio: 'ignore' }
    );
    return result.status === 0 && result.stdout?.trim() === 'OK';
  } catch (e) {
    return false;
  }
}

function findPython() {
  const possibleCommands = ['python3.10', 'python3.11', 'python3.12', 'python3', 'python'];
  
  for (const cmd of possibleCommands) {
    try {
      if (checkPythonVersion(cmd)) {
        if (checkPythonPackage(cmd, 'discord_py_self_mcp') && checkPythonPackage(cmd, 'mcp')) {
          return cmd;
        }
      }
    } catch (e) {
    }
  }
  return null;
}

function checkPythonPackage(pythonCmd) {
  try {
    const result = spawnSync(
      pythonCmd,
      ['-c', 'import discord_py_self_mcp'],
      { stdio: 'ignore' }
    );
    return result.status === 0;
  } catch (e) {
    return false;
  }
}

async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes('--version') || argv.includes('-v')) {
    const v = readPackageVersion();
    if (v) {
      console.log(v);
      process.exit(0);
    }
  }

  if (argv.includes('--help') || argv.includes('-h')) {
    console.log('discord-selfbot-mcp (Node.js wrapper)');
    console.log('Starts the underlying Python MCP server (stdio).');
    console.log('');
    console.log('Usage:');
    console.log('  discord-selfbot-mcp');
    console.log('  discord-selfbot-mcp --version');
    console.log('');
    console.log('Environment:');
    console.log('  DISCORD_TOKEN (required)');
    process.exit(0);
  }

  const pythonCmd = findPython();

  if (!pythonCmd) {
    console.error('Error: Python 3.10+ not found. Please install Python 3.10 or higher.');
    console.error('');
    console.error('Checked Python commands:');
    for (const cmd of ['python3.10', 'python3.11', 'python3.12', 'python3', 'python']) {
      const result = spawnSync(cmd, ['--version'], { stdio: 'ignore' });
      if (result.status === 0) {
        console.error(`  - \${cmd}: found`);
      }
    }
    process.exit(1);
  }

  if (!checkPythonPackage(pythonCmd, 'discord_py_self_mcp')) {
    console.error(`Error: discord-py-self-mcp Python package not found in ${pythonCmd}.`);
    console.error('');
    console.error('Checked Python commands:');
    for (const cmd of ['python3.10', 'python3.11', 'python3.12', 'python3', 'python']) {
      if (checkPythonVersion(cmd) && checkPythonPackage(cmd, 'discord_py_self_mcp')) {
        const mcpInstalled = checkPythonPackage(cmd, 'mcp') ? 'with mcp' : 'without mcp';
        console.error(`  - ${cmd}: has discord_py_self_mcp ${mcpInstalled}`);
      }
    }
    console.error('');
    console.error('To install: pip install -e .');
    console.error('Or: uv tool install git+https://github.com/Microck/discord.py-self-mcp.git');
    process.exit(1);
  }

  if (!checkPythonPackage(pythonCmd, 'mcp')) {
    console.error(`Error: mcp module not found in ${pythonCmd}.`);
    console.error('');
    console.error('Checked Python commands:');
    for (const cmd of ['python3', 'python', 'python3.10', 'python3.11', 'python3.12']) {
      if (checkPythonVersion(cmd) && checkPythonPackage(cmd, 'mcp')) {
        console.error(`  - ${cmd}: has mcp`);
      }
    }
    console.error('');
    console.error('To install: pip install mcp');
    console.error('Or ensure discord-py-self-mcp is installed with all dependencies');
    process.exit(1);
  }

  const proc = spawn(pythonCmd, ['-m', 'discord_py_self_mcp.main', ...argv], {
    stdio: 'inherit',
    env: {
      ...process.env,
      PATH: process.env.PATH
    }
  });

  proc.on('error', (err) => {
    console.error('Failed to start Python MCP server:', err.message);
    process.exit(1);
  });

  proc.on('exit', (code) => {
    process.exit(code ?? 0);
  });

  process.on('SIGTERM', () => proc.kill('SIGTERM'));
  process.on('SIGINT', () => proc.kill('SIGINT'));
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
