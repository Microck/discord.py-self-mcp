import sys


def log_to_stderr(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def mask_secret(secret: str | None) -> str:
    if not secret:
        return "<missing>"
    return "<configured>"
