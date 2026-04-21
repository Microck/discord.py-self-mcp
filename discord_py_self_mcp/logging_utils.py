import sys


def log_to_stderr(message: str) -> None:
    """Write a message to stderr with an implicit newline."""
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def mask_secret(secret: str | None, visible_prefix: int = 4) -> str:
    """Return a masked version of a secret showing only the first few characters."""
    if not secret:
        return "<missing>"

    prefix = secret[:visible_prefix]
    return f"{prefix}... (len={len(secret)})"
