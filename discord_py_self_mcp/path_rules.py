"""Lexical path rules shared by the upload helpers and the command-line client.

Deliberately free of third-party imports: ``scripts/dcli.py`` ships in the npm
package separately from the Python one, so validating a path string must not
require ``discord.py`` to be importable.

The path functions are chosen explicitly from ``ntpath`` or ``posixpath`` rather
than taken from ``os.path``, which is bound to the host at import. That keeps the
Windows rules meaningful on a Linux checkout, where the CI runs, instead of
silently evaluating them with the wrong separator.
"""

import ntpath
import os
import posixpath

ON_WINDOWS = os.name == "nt"

# The host's path flavour. One binding selects every host-dependent behaviour
# (``isabs``, ``basename``), so a test can evaluate the rules for the other
# platform by replacing it together with ON_WINDOWS.
_pathmod = ntpath if ON_WINDOWS else posixpath

# The Windows rules are gated on ON_WINDOWS before they are reached, and UNC and
# drive-relative paths have no POSIX meaning at all, so these use ntpath directly.
# Routing them through the host module would make them change meaning on a Linux
# checkout instead of being the same rules a Windows user gets.
_win = ntpath


def _is_within(path: str, root: str) -> bool:
    """Containment for a local path, coping with roots ending in a separator."""
    path = _pathmod.normcase(path)
    root = _pathmod.normcase(root)
    if path == root:
        return True
    trimmed = root.rstrip(_pathmod.sep)
    if not trimmed:
        # root was a filesystem root such as "/" or "C:\\"
        return path.startswith(_pathmod.normcase(root))
    return path.startswith(trimmed + _pathmod.sep)


def _is_within_unc(path: str, root: str) -> bool:
    """Containment between two UNC paths, which are always Windows-shaped."""
    path = _win.normcase(path)
    root = _win.normcase(root)
    if path == root:
        return True
    trimmed = root.rstrip(_win.sep)
    if not trimmed:
        return path.startswith(_win.normcase(root))
    return path.startswith(trimmed + _win.sep)


def _is_separator_pair(path: str) -> bool:
    """True when a path opens with two separators.

    Windows treats any pair of slashes as the UNC prefix, including the mixed
    ``\\/server\\share`` spelling, so the test cannot just look for two backslashes.
    """
    return len(path) >= 2 and path[0] in "/\\" and path[1] in "/\\"


def _is_unc_path(path: str) -> bool:
    """True for a Windows UNC path, in any slash flavour.

    Detection is purely lexical and never touches the filesystem: the point of this
    predicate is to decide what not to resolve.
    """
    return ON_WINDOWS and _is_separator_pair(path)


def _unc_as_written(path: str) -> str:
    """A UNC path in backslash form, as written, without resolving it.

    Folding every slash also turns a mixed leading pair into the canonical ``\\\\``.
    """
    return path.replace("/", "\\")


def _has_ambiguous_unc_component(path: str) -> bool:
    """Win32 can interpret trailing periods and spaces differently from a lexical check."""
    return any(part.endswith((".", " ")) for part in _unc_parts(path))


def _unc_parts(path: str) -> list[str]:
    """The non-empty components of a UNC path, in backslash form."""
    return [part for part in _unc_as_written(path).split("\\") if part]


def _is_unc_root_of_at_least_a_share(path: str) -> bool:
    """True when a UNC path names a share, not merely a server.

    ``\\\\fileserv`` on its own would authorise every share on that server, which is
    a much wider grant than an operator means when they list one directory.
    """
    return len(_unc_parts(path)) >= 2


def _win32_namespace_error(path: str) -> str | None:
    """Refuse the Win32 file-namespace forms that are not plain server paths.

    ``\\\\?\\`` suppresses normalisation and ``\\\\.\\`` names a device. Neither is
    something a caller needs in order to upload a report, and both change how the
    checks below read the path, so they are refused rather than reasoned about.
    """
    if not _is_separator_pair(path):
        return None
    # the prefix is the third character whatever the slash flavour, so the shape is
    # judged on one spelling
    if path[2:3] in ("?", "."):
        return (
            f"Path {path} uses a Windows file-namespace prefix that cannot be "
            "checked against UPLOAD_DIRS. Use a plain path such as "
            "C:\\uploads\\file.png"
        )
    return None


def _drive_relative_error(path: str) -> str | None:
    """Refuse Windows paths whose meaning depends on the current drive.

    ``\\notes.txt`` is anchored to a drive without naming one and ``D:notes.txt``
    names a drive without being rooted. ``isabs()`` accepts the first and rejects
    the second, and both resolve against whichever drive the process happens to be
    on, so neither can be confined to UPLOAD_DIRS meaningfully.
    """
    if _is_separator_pair(path):
        return None  # UNC and namespace forms are handled elsewhere
    drive, rest = _win.splitdrive(path)
    rooted = rest[:1] in ("/", "\\")
    if (drive or rooted) and not (drive and rooted):
        return (
            f"Path {path!r} is not fully qualified; give a full path such as "
            "C:\\uploads\\file.png"
        )
    return None


def path_qualification_error(path: str) -> str | None:
    """Reject a path whose meaning depends on state the reader does not share.

    This is the rule the CLI applies before prepending its own working directory: a
    Windows path anchored to a drive without naming one, or using a file-namespace
    prefix, stays ambiguous however much is prepended to it.
    """
    if ON_WINDOWS:
        return _win32_namespace_error(path) or _drive_relative_error(path)
    return None


def path_shape_error(path: str) -> str | None:
    """Reject spellings that are empty, relative or ambiguous on this platform.

    Used by the surfaces that read the file, where the path must already be
    absolute. The CLI applies :func:`path_qualification_error` instead, because
    resolving a relative path against its own working directory is the point there.
    """
    if not path:
        return "file_paths contains an empty path"
    error = path_qualification_error(path)
    if error:
        return error
    if not _pathmod.isabs(path):
        return f"file_paths must be absolute, got: {path}"
    return None


def display_name(path: str) -> str:
    """The attachment name for a caller path: its last component, as spelled.

    Only this platform's separators end a component. Backslash is an ordinary
    character in a POSIX filename, so stripping it would turn a file called
    ``notes\\2026`` into one called ``2026``. Windows accepts both flavours, so
    there both are trimmed.
    """
    trailing = _pathmod.sep + (_pathmod.altsep or "")
    return _pathmod.basename(path.rstrip(trailing))


def check_unc_confinement(path: str, roots: list[str]) -> str | None:
    """Containment for a UNC path, decided without resolving it.

    ``realpath()`` on a UNC path contacts the named server and can block for tens
    of seconds on a dead host or a pending authentication prompt, so a network
    destination is compared as written. That is deliberately stricter than the
    local case: nothing is folded away, so ``..`` is refused outright instead of
    being resolved and then judged.

    Comparing text also means a link or reparse point inside an approved share is
    not followed and checked. A configured share is therefore trusted to hold no
    pointer that leaves it.
    """
    if _has_ambiguous_unc_component(path):
        return (
            f"UNC path {path} contains a component ending in a period or space "
            "(including '..'). Name the file directly inside an allowed upload share."
        )
    normalised = _unc_as_written(path)
    for root in roots:
        if not _is_unc_path(root):
            continue
        if _is_within_unc(normalised, _unc_as_written(root)):
            return None
    return (
        f"File {path} is outside the directories this server may upload from. "
        "Add its share to UPLOAD_DIRS."
    )
