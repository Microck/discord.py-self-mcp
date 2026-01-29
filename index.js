#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

function findPython() {
  const possibleCommands = ['python3', 'python', 'python3.10', 'python3.11', 'python3.12'];
  for (const cmd of possibleCommands) {
    try {
      const result = spawn.sync(cmd, ['--version'], { stdio: 'ignore' });
      if (result.status === 0) {
        return cmd;
      }
    } catch (e) {
    }
  }
  return null;
}

function checkPythonPackage(pythonCmd) {
  try {
    const result = spawn.sync(
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
  const pythonCmd = findPython();

  if (!pythonCmd) {
    console.error('Error: Python 3.10+ not found. Please install Python 3.10 or higher.');
    process.exit(1);
  }

  if (!checkPythonPackage(pythonCmd)) {
    console.error('Error: discord-py-self-mcp Python package not installed.');
    console.error('Run: pip install git+https://github.com/Microck/discord.py-self-mcp.git');
    console.error('Or: uv tool install git+https://github.com/Microck/discord.py-self-mcp.git');
    process.exit(1);
  }

  const pythonScript = spawn.sync(
    pythonCmd,
    ['-c', 'import discord_py_self_mcp.main as m; print(m.__file__)'],
    { encoding: 'utf-8' }
  );

  if (pythonScript.stderr && pythonScript.stderr.includes('ModuleNotFoundError')) {
    console.error('Error: discord-py-self-mcp not found. Install it first.');
    console.error('pip install git+https://github.com/Microck/discord.py-self-mcp.git');
    process.exit(1);
  }

  const mainPath = pythonScript.stdout.trim();
  const mainDir = path.dirname(mainPath);

  const proc = spawn(pythonCmd, ['-m', 'discord_py_self_mcp.main'], {
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
