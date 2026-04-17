import asyncio
import os
import shutil
from pathlib import Path

from mcp.types import TextContent, ImageContent, EmbeddedResource

from .registry import registry


DEFAULT_TIMEOUT_SECONDS = 180
MAX_OUTPUT_CHARS = 12000
DEFAULT_DISCRAWL_BINARY = "discrawl"


Response = list[TextContent | ImageContent | EmbeddedResource]


def _text(value: str) -> Response:
    """Wrap a plain-text string into a single-element MCP response list.

    Args:
        value: The text content to wrap.

    Returns:
        Response: A list containing one :class:`TextContent` element.
    """
    output: Response = [TextContent(type="text", text=value)]
    return output


def _default_discrawl_candidates() -> list[str]:
    """Return candidate file paths for the discrawl binary.

    Checks the sibling ``discrawl-self/bin/discrawl`` path relative to
    the repository root, then falls back to the bare ``discrawl`` name
    for ``PATH`` resolution.

    Returns:
        list[str]: A list of candidate binary paths.
    """
    repo_root = Path(__file__).resolve().parents[2]
    workspace_dir = repo_root.parent
    return [
        str(workspace_dir / "discrawl-self" / "bin" / "discrawl"),
        DEFAULT_DISCRAWL_BINARY,
    ]


def _resolve_discrawl_binary(arguments: dict) -> str:
    """Determine the discrawl binary path from arguments, env, or defaults.

    Checks the ``binary`` argument key, then the ``DISCRAWL_BIN``
    environment variable, and finally the default candidate list.

    Args:
        arguments: The tool arguments dictionary.

    Returns:
        str: The resolved binary path or name.
    """
    explicit = str(arguments.get("binary") or os.getenv("DISCRAWL_BIN") or "").strip()
    if explicit:
        return explicit

    for candidate in _default_discrawl_candidates():
        if _binary_exists(candidate):
            return candidate

    return DEFAULT_DISCRAWL_BINARY


def _truncate_output(value: str) -> str:
    """Truncate output text to ``MAX_OUTPUT_CHARS`` characters.

    Args:
        value: The text to potentially truncate.

    Returns:
        str: The original text if within the limit, or a truncated version
            with an ellipsis suffix.
    """
    if len(value) <= MAX_OUTPUT_CHARS:
        return value
    return value[:MAX_OUTPUT_CHARS] + "\n... output truncated ..."


def _binary_exists(binary: str) -> bool:
    """Check whether a binary exists on disk or on the system ``PATH``.

    Args:
        binary: The binary name or absolute/relative path.

    Returns:
        bool: ``True`` if the binary is found.
    """
    if not binary:
        return False
    if shutil.which(binary):
        return True
    return Path(binary).expanduser().exists()


async def _run_discrawl(
    arguments: dict,
) -> Response:
    """Execute a discrawl CLI command as a subprocess.

    This is an async method that builds the command line from the provided
    arguments, runs the process with a timeout, and returns the captured
    stdout and stderr.

    Args:
        arguments: A dictionary with keys ``command`` (str), optionally
            ``args`` (list[str]), ``config_path`` (str), ``binary`` (str),
            and ``timeout_seconds`` (int).

    Returns:
        Response: A single-element list with the combined command output
            or an error message.
    """
    command = str(arguments.get("command", "")).strip()
    if not command:
        return _text("Missing required field: command")

    args = arguments.get("args", [])
    if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
        return _text("args must be an array of strings")

    timeout_seconds = arguments.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError):
        return _text("timeout_seconds must be an integer")

    if timeout_seconds < 5 or timeout_seconds > 1800:
        return _text("timeout_seconds must be between 5 and 1800 seconds")

    binary = _resolve_discrawl_binary(arguments)
    if not _binary_exists(binary):
        return _text(
            (
                f"Could not find discrawl binary: {binary}\n"
                "Build discrawl-self at ../discrawl-self/bin/discrawl or set DISCRAWL_BIN to the executable path."
            )
        )

    cmd = [binary]
    config_path = str(arguments.get("config_path", "")).strip()
    if config_path:
        cmd.extend(["--config", config_path])
    cmd.append(command)
    cmd.extend(args)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return _text(
            (
                f"discrawl command timed out after {timeout_seconds}s\n"
                f"command={' '.join(cmd)}"
            )
        )

    stdout_text = _truncate_output(stdout.decode("utf-8", errors="replace").strip())
    stderr_text = _truncate_output(stderr.decode("utf-8", errors="replace").strip())

    parts = [
        f"command={' '.join(cmd)}",
        f"exit_code={process.returncode}",
    ]
    if stdout_text:
        parts.append("stdout:\n" + stdout_text)
    if stderr_text:
        parts.append("stderr:\n" + stderr_text)

    if not stdout_text and not stderr_text:
        parts.append("No output")

    return _text("\n\n".join(parts))


@registry.register(
    name="run_discrawl",
    description="Run a discrawl CLI command with options",
    input_schema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "discrawl subcommand, e.g. doctor, sync, search, status",
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "subcommand args and flags as array items",
            },
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path; defaults to DISCRAWL_BIN or discrawl",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 180,
            },
        },
        "required": ["command"],
    },
)
async def run_discrawl(arguments: dict) -> Response:
    """Run an arbitrary discrawl CLI command via the MCP interface.

    This is an async MCP tool handler that delegates to
    :func:`_run_discrawl`.

    Args:
        arguments: A dictionary with ``command`` (str) and optional
            ``args``, ``config_path``, ``binary``, and ``timeout_seconds``.

    Returns:
        Response: The command output or error message.
    """
    return await _run_discrawl(arguments)


def _base_discrawl_arguments(arguments: dict, command: str, args: list[str]) -> dict:
    """Build a minimal arguments dict for a discrawl subcommand.

    Copies ``config_path``, ``binary``, and ``timeout_seconds`` from the
    original arguments when present.

    Args:
        arguments: The original MCP tool arguments.
        command: The discrawl subcommand name.
        args: Positional arguments and flags for the subcommand.

    Returns:
        dict: A new arguments dictionary suitable for :func:`_run_discrawl`.
    """
    payload = {
        "command": command,
        "args": args,
    }
    for key in ("config_path", "binary", "timeout_seconds"):
        if key in arguments and arguments[key] is not None:
            payload[key] = arguments[key]
    return payload


def _append_value(args: list[str], flag: str, value: object) -> None:
    """Append a CLI flag and its value to an argument list.

    Skips empty or whitespace-only values.

    Args:
        args: The argument list to modify in-place.
        flag: The flag name (e.g. ``--guild``).
        value: The value to stringify and append.
    """
    text = str(value).strip()
    if text:
        args.extend([flag, text])


@registry.register(
    name="discrawl_doctor",
    description="Run discrawl doctor",
    input_schema={
        "type": "object",
        "properties": {
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 180,
            },
        },
    },
)
async def discrawl_doctor(arguments: dict) -> Response:
    """Run the ``discrawl doctor`` diagnostic subcommand.

    This is an async MCP tool handler.

    Args:
        arguments: Optional keys ``config_path``, ``binary``, and
            ``timeout_seconds``.

    Returns:
        Response: The diagnostic output or error message.
    """
    return await _run_discrawl(_base_discrawl_arguments(arguments, "doctor", []))


@registry.register(
    name="discrawl_status",
    description="Run discrawl status",
    input_schema={
        "type": "object",
        "properties": {
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 180,
            },
        },
    },
)
async def discrawl_status(arguments: dict) -> Response:
    """Run the ``discrawl status`` subcommand.

    This is an async MCP tool handler.

    Args:
        arguments: Optional keys ``config_path``, ``binary``, and
            ``timeout_seconds``.

    Returns:
        Response: The status output or error message.
    """
    return await _run_discrawl(_base_discrawl_arguments(arguments, "status", []))


@registry.register(
    name="discrawl_sync",
    description="Run discrawl sync with typed options",
    input_schema={
        "type": "object",
        "properties": {
            "guild": {
                "type": "string",
                "description": "single guild id",
            },
            "guilds": {
                "type": "string",
                "description": "comma-separated guild ids",
            },
            "channels": {
                "type": "string",
                "description": "comma-separated channel ids",
            },
            "since": {
                "type": "string",
                "description": "RFC3339 timestamp",
            },
            "concurrency": {
                "type": "integer",
                "description": "sync concurrency value",
            },
            "full": {
                "type": "boolean",
                "description": "run full sync",
            },
            "with_embeddings": {
                "type": "boolean",
                "description": "enable embedding job enqueue during sync",
            },
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 300,
            },
        },
    },
)
async def discrawl_sync(arguments: dict) -> Response:
    """Run the ``discrawl sync`` subcommand with typed options.

    This is an async MCP tool handler that translates the provided options
    into the appropriate CLI flags.

    Args:
        arguments: A dictionary with optional keys ``guild``, ``guilds``,
            ``channels``, ``since``, ``concurrency``, ``full``,
            ``with_embeddings``, ``config_path``, ``binary``, and
            ``timeout_seconds``.

    Returns:
        Response: The sync output or error message.
    """
    args: list[str] = []
    if arguments.get("full") is True:
        args.append("--full")
    if arguments.get("with_embeddings") is True:
        args.append("--with-embeddings")

    if arguments.get("guild") is not None:
        _append_value(args, "--guild", arguments["guild"])
    if arguments.get("guilds") is not None:
        _append_value(args, "--guilds", arguments["guilds"])
    if arguments.get("channels") is not None:
        _append_value(args, "--channels", arguments["channels"])
    if arguments.get("since") is not None:
        _append_value(args, "--since", arguments["since"])
    if arguments.get("concurrency") is not None:
        _append_value(args, "--concurrency", arguments["concurrency"])

    return await _run_discrawl(_base_discrawl_arguments(arguments, "sync", args))


@registry.register(
    name="discrawl_search",
    description="Run discrawl search with typed options",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "search query text",
            },
            "guild": {
                "type": "string",
                "description": "guild id",
            },
            "channel": {
                "type": "string",
                "description": "channel id or name",
            },
            "author": {
                "type": "string",
                "description": "author id or name",
            },
            "limit": {
                "type": "integer",
                "description": "max number of rows",
            },
            "include_empty": {
                "type": "boolean",
                "description": "include rows with no searchable content",
            },
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 180,
            },
        },
        "required": ["query"],
    },
)
async def discrawl_search(arguments: dict) -> Response:
    """Run the ``discrawl search`` subcommand with typed options.

    This is an async MCP tool handler that performs a full-text search
    across indexed Discord messages.

    Args:
        arguments: A dictionary with ``query`` (str) and optional keys
            ``guild``, ``channel``, ``author``, ``limit``,
            ``include_empty``, ``config_path``, ``binary``, and
            ``timeout_seconds``.

    Returns:
        Response: The search results or error message.
    """
    query = str(arguments.get("query", "")).strip()
    if not query:
        return _text("Missing required field: query")

    args: list[str] = []
    if arguments.get("guild") is not None:
        _append_value(args, "--guild", arguments["guild"])
    if arguments.get("channel") is not None:
        _append_value(args, "--channel", arguments["channel"])
    if arguments.get("author") is not None:
        _append_value(args, "--author", arguments["author"])
    if arguments.get("limit") is not None:
        _append_value(args, "--limit", arguments["limit"])
    if arguments.get("include_empty") is True:
        args.append("--include-empty")
    args.append(query)

    return await _run_discrawl(_base_discrawl_arguments(arguments, "search", args))


@registry.register(
    name="discrawl_messages",
    description="Run discrawl messages with typed options",
    input_schema={
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "description": "channel id or name",
            },
            "author": {
                "type": "string",
                "description": "author id or name",
            },
            "guild": {
                "type": "string",
                "description": "guild id",
            },
            "since": {
                "type": "string",
                "description": "RFC3339 timestamp",
            },
            "days": {
                "type": "integer",
                "description": "messages since now minus days",
            },
            "limit": {
                "type": "integer",
                "description": "max number of rows",
            },
            "all": {
                "type": "boolean",
                "description": "remove default row cap",
            },
            "include_empty": {
                "type": "boolean",
                "description": "include rows with no displayable content",
            },
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 180,
            },
        },
    },
)
async def discrawl_messages(arguments: dict) -> Response:
    """Run the ``discrawl messages`` subcommand with typed options.

    This is an async MCP tool handler that retrieves stored messages from
    the discrawl index.

    Args:
        arguments: A dictionary with optional keys ``channel``, ``author``,
            ``guild``, ``since``, ``days``, ``limit``, ``all``,
            ``include_empty``, ``config_path``, ``binary``, and
            ``timeout_seconds``.

    Returns:
        Response: The message rows or error message.
    """
    args: list[str] = []
    if arguments.get("channel") is not None:
        _append_value(args, "--channel", arguments["channel"])
    if arguments.get("author") is not None:
        _append_value(args, "--author", arguments["author"])
    if arguments.get("guild") is not None:
        _append_value(args, "--guild", arguments["guild"])
    if arguments.get("since") is not None:
        _append_value(args, "--since", arguments["since"])
    if arguments.get("days") is not None:
        _append_value(args, "--days", arguments["days"])
    if arguments.get("limit") is not None:
        _append_value(args, "--limit", arguments["limit"])
    if arguments.get("all") is True:
        args.append("--all")
    if arguments.get("include_empty") is True:
        args.append("--include-empty")

    return await _run_discrawl(_base_discrawl_arguments(arguments, "messages", args))


@registry.register(
    name="discrawl_mentions",
    description="Run discrawl mentions with typed options",
    input_schema={
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "mention target id or name",
            },
            "type": {
                "type": "string",
                "description": "mention type: user or role",
            },
            "channel": {
                "type": "string",
                "description": "channel id or name",
            },
            "guild": {
                "type": "string",
                "description": "guild id",
            },
            "since": {
                "type": "string",
                "description": "RFC3339 timestamp",
            },
            "days": {
                "type": "integer",
                "description": "mentions since now minus days",
            },
            "limit": {
                "type": "integer",
                "description": "max number of rows",
            },
            "config_path": {
                "type": "string",
                "description": "optional --config path for discrawl",
            },
            "binary": {
                "type": "string",
                "description": "optional discrawl binary path",
            },
            "timeout_seconds": {
                "type": "integer",
                "description": "max command runtime in seconds (5-1800)",
                "default": 180,
            },
        },
    },
)
async def discrawl_mentions(arguments: dict) -> Response:
    """Run the ``discrawl mentions`` subcommand with typed options.

    This is an async MCP tool handler that retrieves messages containing
    mentions of a specific user or role from the discrawl index.

    Args:
        arguments: A dictionary with optional keys ``target``, ``type``
            (``"user"`` or ``"role"``), ``channel``, ``guild``, ``since``,
            ``days``, ``limit``, ``config_path``, ``binary``, and
            ``timeout_seconds``.

    Returns:
        Response: The mention rows or error message.
    """
    mention_type = arguments.get("type")
    if mention_type is not None:
        text = str(mention_type).strip().lower()
        if text not in ("user", "role"):
            return _text('type must be "user" or "role"')
        arguments = dict(arguments)
        arguments["type"] = text

    args: list[str] = []
    if arguments.get("target") is not None:
        _append_value(args, "--target", arguments["target"])
    if arguments.get("type") is not None:
        _append_value(args, "--type", arguments["type"])
    if arguments.get("channel") is not None:
        _append_value(args, "--channel", arguments["channel"])
    if arguments.get("guild") is not None:
        _append_value(args, "--guild", arguments["guild"])
    if arguments.get("since") is not None:
        _append_value(args, "--since", arguments["since"])
    if arguments.get("days") is not None:
        _append_value(args, "--days", arguments["days"])
    if arguments.get("limit") is not None:
        _append_value(args, "--limit", arguments["limit"])

    return await _run_discrawl(_base_discrawl_arguments(arguments, "mentions", args))
