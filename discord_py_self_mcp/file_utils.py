"""Helpers for attaching local files to outgoing messages.

Shared by the MCP tools and the CLI daemon so both surfaces resolve paths,
enforce limits and read bytes in exactly the same way.

Security note: these helpers read files from the machine running the server and
hand them to Discord. Anyone who can call ``send_message`` can therefore publish
any file the server process can read, so uploads require the operator to name the
directory trees they allow via ``UPLOAD_DIRS``.
"""

import asyncio
import io
import os
import stat
from pathlib import Path

import discord
from dotenv import load_dotenv
from dotenv.main import DotEnv

from . import path_rules

# Seam for the tests: every resolution of a caller path goes through here, so a
# test can prove that a network path is never resolved at all.
_realpath = os.path.realpath

# Discord's per-file ceiling depends on the account's Nitro tier and the target
# server's boost level, so it is not something the library can hardcode. 8 MiB is
# a conservative default that every account can send; raise it with
# MAX_UPLOAD_BYTES when the channel you are posting to allows larger files.
MAX_UPLOAD_BYTES_DEFAULT = 8 * 1024 * 1024

# Discord rejects messages that carry more than this many files.
MAX_FILES_PER_MESSAGE = 10

# The Create Message request is capped at 25 MiB including multipart overhead, so
# keep the combined size of one message's files below that.
MAX_UPLOAD_TOTAL_BYTES_DEFAULT = 20 * 1024 * 1024

# Bound the number of in-memory batches being prepared, rate limited or sent.
_upload_slots = asyncio.Semaphore(2)


class UploadError(Exception):
    """A request was refused; its message is returned to the caller."""


def load_runtime_dotenv(path):
    """Only the inherited environment and the installation's .env may grant uploads."""
    python_env = Path(__file__).resolve().parents[1] / ".env"
    if str(path) == str(python_env):
        load_dotenv(python_env)
        return

    # The npm scripts and Python package can live in separate directories.
    # Resolve the Python installation's upload settings before reading any of
    # the launch directory's variables, including interpolation inputs.
    if os.getenv("PYTHON_DOTENV_DISABLED", "").casefold() in {"1", "true", "t", "yes", "y"}:
        return
    upload_keys = {"UPLOAD_DIRS", "MAX_UPLOAD_BYTES", "MAX_UPLOAD_TOTAL_BYTES"}
    for source, uploads_only in ((python_env, True), (path, False)):
        if not source.is_file():
            continue
        # DotEnv with override=False uses the same interpolation precedence as
        # load_dotenv, while letting us select keys before changing os.environ.
        for name, value in DotEnv(source, override=False, encoding="utf-8").dict().items():
            env_name = name.upper() if os.name == "nt" else name
            if (env_name in upload_keys) == uploads_only and value is not None:
                os.environ.setdefault(name, value)


def _positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "")
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def max_upload_bytes() -> int:
    """Per-file size ceiling, overridable through the MAX_UPLOAD_BYTES env var."""
    return _positive_int_env("MAX_UPLOAD_BYTES", MAX_UPLOAD_BYTES_DEFAULT)


def max_upload_total_bytes() -> int:
    """Combined ceiling for one message, via MAX_UPLOAD_TOTAL_BYTES."""
    return _positive_int_env("MAX_UPLOAD_TOTAL_BYTES", MAX_UPLOAD_TOTAL_BYTES_DEFAULT)


def _upload_roots() -> list[str]:
    """Resolved directory trees uploads may read from, from UPLOAD_DIRS."""
    raw = os.getenv("UPLOAD_DIRS", "")
    roots = []
    for entry in raw.split(os.pathsep):
        if not entry.strip() or path_rules.path_shape_error(entry):
            continue
        if path_rules._is_unc_path(entry):
            # resolving a UNC root would contact that server on every request, so
            # an operator-named share is trusted as written instead of probed
            if path_rules._has_ambiguous_unc_component(entry):
                continue
            if not path_rules._is_unc_root_of_at_least_a_share(entry):
                # a bare server would authorise every share on it
                continue
            roots.append(path_rules._unc_as_written(entry))
            continue
        try:
            resolved = _realpath(entry, strict=True)
        except (OSError, ValueError):
            continue
        if os.path.isdir(resolved):
            roots.append(resolved)
        else:
            # a configured-but-missing root is a misconfiguration, not a licence
            # to upload anything, so it is dropped rather than trusted
            continue
    return roots


def _is_regular(handle) -> bool:
    """True when an open file descriptor refers to a regular file.

    Checked after opening rather than from a stat of the pathname, so a symlink or
    a replacement between the pre-flight pass and the read cannot smuggle in a
    device or a pipe.
    """
    return stat.S_ISREG(os.fstat(handle.fileno()).st_mode)


def _open_upload_fd(path, flags):
    # A special file can replace the checked path before open. On POSIX a FIFO
    # must open without waiting for a writer so fstat can reject it promptly.
    return os.open(path, flags | getattr(os, "O_NONBLOCK", 0))


def normalize_file_paths(file_paths) -> list[str]:
    """Accept one path or a list of paths and return them unchanged.

    MCP clients serialise a single file differently from the CLI and callers often
    have exactly one path in hand, so both shapes are accepted. Paths are not
    stripped or otherwise rewritten: on POSIX a trailing space is a valid
    filename, and silently dropping blank entries would let a request that asked
    for two attachments send one.
    """
    if file_paths is None:
        return []
    if isinstance(file_paths, str):
        return [file_paths]
    if isinstance(file_paths, (bytes, bytearray)):
        raise ValueError("file_paths must be a string or a list of strings")
    if not isinstance(file_paths, (list, tuple)):
        raise ValueError("file_paths must be a string or a list of strings")

    paths = []
    for entry in file_paths:
        if not isinstance(entry, str):
            raise ValueError("file_paths must contain only strings")
        paths.append(entry)
    return paths


def _missing_in_upload_dir(path: str, roots: list[str]) -> bool:
    """Report a missing leaf only after confirming its parent is authorized."""
    parent, name = os.path.split(path)
    if name in ("", ".", "..") or os.path.splitdrive(name)[0]:
        return False
    try:
        parent = _realpath(parent, strict=True)
    except (OSError, ValueError):
        return False
    if not any(path_rules._is_within(parent, root) for root in roots):
        return False
    # A dangling symlink exists as a directory entry. Keep the state of its
    # unresolved target private.
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    except (OSError, ValueError):
        pass
    return False


def _resolve_for_upload(path: str, roots: list[str]) -> tuple[str | None, str | None]:
    """Resolve a caller path for reading, or explain why it may not be read.

    Returns ``(path_to_open, None)`` or ``(None, error)``. Local paths are resolved
    through symlinks and then confined; UNC paths are confined as written and never
    resolved, because resolving one contacts its server. Both surfaces go through
    here so the pre-flight pass and the read cannot disagree.
    """
    if path_rules._is_unc_path(path):
        error = path_rules.check_unc_confinement(path, roots)
        if error:
            return None, error
        return path_rules._unc_as_written(path), None

    try:
        resolved = _realpath(path, strict=True)
    except FileNotFoundError:
        if _missing_in_upload_dir(path, roots):
            return None, f"File not found: {path}"
    except (OSError, ValueError):
        pass
    else:
        if any(path_rules._is_within(resolved, root) for root in roots):
            return resolved, None
    return None, (
        f"File {path} is unavailable or outside the directories this server may upload from. "
        "Check the path and UPLOAD_DIRS."
    )


def validate_file_paths(file_paths) -> str | None:
    """Check a path list without reading anything. Returns an error or None.

    A cheap pre-flight pass: it rejects unusable requests before the rate limiter
    is consulted and before any bytes are read. The authoritative checks happen in
    :func:`build_files`, against the opened file.
    """
    try:
        paths = normalize_file_paths(file_paths)
    except ValueError as exc:
        return str(exc)

    if not paths:
        return None

    if len(paths) > MAX_FILES_PER_MESSAGE:
        return (
            f"Too many files: Discord accepts at most {MAX_FILES_PER_MESSAGE} "
            f"attachments per message (got {len(paths)})"
        )

    roots = _upload_roots()
    if not roots:
        raw = os.getenv("UPLOAD_DIRS", "")
        if raw.strip():
            return (
                "UPLOAD_DIRS is set but names no existing directory, so uploads "
                "are refused. Point it at directories that exist."
            )
        return (
            "File uploads are not enabled on this server. Set UPLOAD_DIRS to a "
            "list of directories that may be uploaded from."
        )

    for path in paths:
        error = path_rules.path_shape_error(path)
        if error:
            return error

    for path in paths:
        _target, error = _resolve_for_upload(path, roots)
        if error:
            return error

    per_file = max_upload_bytes()
    total = 0
    for path in paths:
        if not os.path.exists(path):
            return f"File not found: {path}"
        if not os.path.isfile(path):
            return f"Not a file: {path}"
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            return f"Cannot read file {path}: {exc}"
        if size > per_file:
            return (
                f"File {path} is {size} bytes, above the {per_file} byte limit. "
                "Raise MAX_UPLOAD_BYTES if the target channel allows larger uploads."
            )
        total += size

    total_limit = max_upload_total_bytes()
    if total > total_limit:
        return (
            f"Attachments total {total} bytes, above the {total_limit} byte "
            "combined limit. Raise MAX_UPLOAD_TOTAL_BYTES or send fewer files."
        )
    return None


def build_files(file_paths) -> tuple[list, str | None]:
    """Read each requested file and return it as a ``discord.File``.

    Every file is read into memory, bounded by the configured limits, and handed
    to the library as an in-memory object. That is deliberate:

    * the size limit then applies to the exact bytes that are uploaded, rather
      than to a ``stat`` or a cached ``File.size`` that a growing file can outpace
      before the HTTP layer reads it;
    * no file descriptor is held open across the rate limiter or the upload, so
      there is nothing to leak on an early return and nothing for a concurrent
      burst of calls to exhaust.

    Confinement is re-checked against the resolved path immediately before the
    open, which closes the gap between the pre-flight pass and the read for a
    stable directory tree. It is not a sandbox: a separate process that can rename
    a checked directory in the instant before the open can still redirect the read,
    and on Windows a case-sensitive directory can make two roots that differ only
    by case distinct while the comparison folds them together. Treat the operator
    who sets UPLOAD_DIRS as trusted and keep the directory writable only by people
    who are.

    A network destination is the weaker case. It is confined by comparing the
    pathname as written, because resolving it would contact its server, so a link
    or reparse point inside an approved share is followed by the open without being
    re-checked. Name a share only when you control it.

    Returns ``(files, None)`` on success or ``([], error)`` on failure.
    """
    try:
        paths = normalize_file_paths(file_paths)
    except ValueError as exc:
        return [], str(exc)

    if not paths:
        return [], None

    error = validate_file_paths(paths)
    if error:
        return [], error

    roots = _upload_roots()
    per_file = max_upload_bytes()
    total_limit = max_upload_total_bytes()

    files = []
    total = 0
    try:
        for path in paths:
            resolved, error = _resolve_for_upload(path, roots)
            if error:
                # normally the pre-flight pass already refused this; reaching it
                # here means the tree moved in between, so say what changed rather
                # than reporting a generic refusal
                raise UploadError(error)

            try:
                with open(resolved, "rb", opener=_open_upload_fd) as handle:
                    if not _is_regular(handle):
                        raise UploadError(f"Not a regular file: {path}")
                    # read one byte past the cap so an oversized file is detected
                    # without buffering all of it
                    budget = min(per_file, total_limit - total)
                    data = handle.read(budget + 1)
            except OSError as exc:
                # the opened path is the resolved target, which may be behind a
                # link the caller has no reason to learn about, so report the path
                # they asked for and the reason without its filename
                raise UploadError(
                    f"Cannot read {path}: {exc.strerror or 'read failed'}"
                )

            read_len = len(data)
            if read_len > total_limit - total:
                raise UploadError(
                    f"Attachments would total more than {total_limit} bytes. "
                    "Raise MAX_UPLOAD_TOTAL_BYTES or send fewer files."
                )
            if read_len > per_file:
                raise UploadError(
                    f"File {path} is larger than {per_file} bytes once read. "
                    "Raise MAX_UPLOAD_BYTES if the target channel allows larger uploads."
                )

            total += read_len

            buffer = io.BytesIO(data)
            # the display name comes from the path the caller asked for, not the
            # resolved target: discord.File also derives spoiler handling from it,
            # so a SPOILER_ link would otherwise lose both its name and its flag
            files.append(discord.File(buffer, filename=path_rules.display_name(path)))
    except UploadError as exc:
        error = str(exc)
    except OSError as exc:
        error = f"Cannot read file for sending: {exc}"
    except Exception as exc:
        error = f"Cannot prepare files for sending: {exc}"
    else:
        return files, None

    _close_upload_buffers(files)
    return [], error


def _close_upload_buffers(files):
    for file in files:
        # discord.File temporarily replaces fp.close for retries. Its close()
        # restores the method, but the caller still owns the BytesIO.
        file.close()
        file.fp.close()


def _finish_upload(worker):
    try:
        if not worker.cancelled() and worker.exception() is None:
            files, _ = worker.result()
            _close_upload_buffers(files)
    finally:
        _upload_slots.release()


async def send_with_files(destination, content, file_paths, send_kwargs, rate_limit):
    """Prepare a bounded upload off-loop and acquire the message slot at dispatch."""
    try:
        paths = normalize_file_paths(file_paths)
    except ValueError as exc:
        raise UploadError(str(exc)) from exc
    if not paths:
        await rate_limit("message")
        return await destination.send(content, **send_kwargs), []

    await _upload_slots.acquire()
    worker = asyncio.create_task(asyncio.to_thread(build_files, paths))
    try:
        files, error = await asyncio.shield(worker)
        if error:
            raise UploadError(error)
        await rate_limit("message")
        message = await destination.send(content or None, files=files, **send_kwargs)
        return message, files
    finally:
        # Cancelling an await cannot interrupt a filesystem call. Keep that
        # worker's slot until its read actually finishes.
        if worker.done():
            _finish_upload(worker)
        else:
            worker.add_done_callback(_finish_upload)


def format_file_summary(files) -> str:
    """Render the attachment tail appended to a successful send message."""
    if not files:
        return ""
    names = ", ".join(getattr(handle, "filename", "attachment") for handle in files)
    count = len(files)
    noun = "attachment" if count == 1 else "attachments"
    return f" with {count} {noun}: {names}"


def format_sent_summary(message, files) -> str:
    """Describe the attachments that landed on a sent message.

    Discord renames a file that collides with one already on the message, so the
    names on the returned message are the ones the caller can actually refer to.
    Those are reported when the message carries them; the names we sent are the
    fallback for a message object that exposes no attachment list.
    """
    if not files:
        return ""
    landed = getattr(message, "attachments", None)
    if landed is None:
        return format_file_summary(files)
    if not landed:
        return " (Discord reported no attachments)"
    return format_file_summary(landed)
