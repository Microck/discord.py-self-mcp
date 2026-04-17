import os
from pathlib import Path


APP_NAME = "discord-py-self-mcp"
_DEFAULT_RUNTIME_DIR = Path.home() / ".local" / "state" / APP_NAME


def runtime_dir() -> Path:
    base = os.getenv("XDG_RUNTIME_DIR")
    if base:
        return Path(base) / APP_NAME
    return _DEFAULT_RUNTIME_DIR


RUNTIME_DIR = runtime_dir()
PID_FILE = RUNTIME_DIR / "daemon.pid"
SOCKET_PATH = RUNTIME_DIR / "daemon.sock"
AUTH_FILE = RUNTIME_DIR / "daemon.auth"
LOG_FILE = RUNTIME_DIR / "daemon.log"


def ensure_runtime_dir() -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(RUNTIME_DIR, 0o700)
    return RUNTIME_DIR


def chmod_private(path: Path) -> None:
    os.chmod(path, 0o600)
