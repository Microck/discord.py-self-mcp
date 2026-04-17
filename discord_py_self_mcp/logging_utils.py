import sys


def log_to_stderr(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def mask_secret(secret: str | None, visible_prefix: int = 4) -> str:
    if not secret:
        return "<missing>"

    prefix = secret[:visible_prefix]
    return f"{prefix}... (len={len(secret)})"
