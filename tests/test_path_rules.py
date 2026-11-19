"""Tests for the lexical path rules.

These rules are pure string judgements, so they can be evaluated for either
platform from either host. A fixture replaces both the platform flag and the path
module the rules use, because patching only the flag would leave ``isabs`` bound to
the host and the assertions would mean different things on the CI runner than on a
Windows machine.
"""

import ntpath
import os
import pathlib
import posixpath

import pytest

from discord_py_self_mcp import path_rules


def use_platform(monkeypatch, *, windows):
    """Make the rules evaluate paths as one platform would."""
    monkeypatch.setattr(path_rules, "ON_WINDOWS", windows)
    monkeypatch.setattr(path_rules, "_pathmod", ntpath if windows else posixpath)


@pytest.fixture
def as_windows(monkeypatch):
    use_platform(monkeypatch, windows=True)


@pytest.fixture
def as_posix(monkeypatch):
    use_platform(monkeypatch, windows=False)


class TestWindowsQualification:
    @pytest.mark.parametrize(
        "path",
        [
            "\\notes.txt",  # anchored to a drive, but which one?
            "D:notes.txt",  # names a drive, but is not rooted on it
            "/notes.txt",  # rooted, drive unnamed
        ],
    )
    def test_drive_relative_paths_are_refused(self, as_windows, path):
        error = path_rules.path_shape_error(path)
        assert error is not None
        assert "not fully qualified" in error

    @pytest.mark.parametrize(
        "path",
        [
            r"\\?\C:\uploads\f.txt",
            r"\\.\NUL",
            r"//?/C:/uploads/f.txt",  # same namespace, other slash flavour
            r"//./NUL",
            r"\/?\C:\uploads\f.txt",  # mixed leading pair, same namespace
        ],
    )
    def test_file_namespace_prefixes_are_refused(self, as_windows, path):
        error = path_rules.path_shape_error(path)
        assert error is not None
        assert "namespace prefix" in error

    def test_a_plain_windows_path_is_accepted(self, as_windows):
        assert path_rules.path_shape_error(r"C:\uploads\f.txt") is None

    def test_qualification_alone_still_allows_a_relative_path(self, as_windows):
        # the CLI resolves relative paths against its own working directory, so it
        # must not inherit the "must be absolute" rule
        assert path_rules.path_qualification_error("notes.txt") is None

    def test_posix_is_unaffected_by_the_windows_rules(self, as_posix):
        assert path_rules.path_shape_error("/uploads/f.txt") is None
        assert path_rules.path_shape_error("notes.txt").startswith(
            "file_paths must be absolute"
        )

    def test_empty_path_is_reported(self):
        assert path_rules.path_shape_error("") == "file_paths contains an empty path"


class TestUncDetection:
    @pytest.mark.parametrize(
        "path",
        [
            r"\\fileserv\reports\f.txt",
            r"//fileserv/reports/f.txt",
            r"\/fileserv\reports\f.txt",  # mixed pair: Windows reads this as UNC
            r"/\fileserv/reports/f.txt",
        ],
    )
    def test_every_separator_pair_is_recognised(self, as_windows, path):
        # a spelling that reaches realpath would contact the server, and a dead
        # address was measured blocking for 47 seconds
        assert path_rules._is_unc_path(path) is True

    def test_a_single_leading_separator_is_not_unc(self, as_windows):
        assert path_rules._is_unc_path("\\notes.txt") is False

    def test_posix_never_treats_a_pair_as_unc(self, as_posix):
        assert path_rules._is_unc_path("//fileserv/reports/f.txt") is False

    @pytest.mark.parametrize(
        "path",
        [
            r"\\fileserv\reports\q3.xlsx",
            r"\/fileserv\reports\q3.xlsx",
            r"//fileserv/reports/q3.xlsx",
        ],
    )
    def test_mixed_and_forward_spellings_confine_alike(self, as_windows, path):
        share = r"\\fileserv\reports"
        assert path_rules.check_unc_confinement(path, [share]) is None

    def test_a_sibling_share_is_refused(self, as_windows):
        error = path_rules.check_unc_confinement(
            r"\\fileserv\secrets\k.txt", [r"\\fileserv\reports"]
        )
        assert error is not None
        assert "outside the directories" in error

    def test_traversal_is_refused_rather_than_resolved(self, as_windows):
        error = path_rules.check_unc_confinement(
            r"\\fileserv\reports\..\secrets\k.txt", [r"\\fileserv\reports"]
        )
        assert error is not None
        assert "'..'" in error

    def test_a_local_root_does_not_authorise_a_network_share(self, as_windows):
        # the operator allowed a directory, not the machine hosting it
        assert (
            path_rules.check_unc_confinement(
                r"\\fileserv\reports\q3.xlsx", [r"C:\uploads"]
            )
            is not None
        )

    def test_a_share_name_may_contain_double_dots(self, as_windows):
        assert path_rules._has_dotdot(r"\\fileserv\reports..archive\f.txt") is False
        assert path_rules._has_dotdot(r"\\fileserv\reports\..\f.txt") is True


class TestUncRootShape:
    def test_a_bare_server_is_not_a_usable_root(self):
        # "\\fileserv" alone would authorise every share on that server
        assert path_rules._is_unc_root_of_at_least_a_share(r"\\fileserv") is False
        assert path_rules._is_unc_root_of_at_least_a_share(r"\\fileserv\reports")

    def test_a_mixed_pair_server_is_still_bare(self):
        assert path_rules._is_unc_root_of_at_least_a_share(r"\/fileserv") is False


class TestDisplayNames:
    def test_posix_keeps_a_backslash_in_the_name(self, as_posix):
        # backslash is an ordinary character in a POSIX filename
        assert path_rules.display_name("/uploads/notes\\2026") == "notes\\2026"
        assert path_rules.display_name("/uploads/notes.txt/") == "notes.txt"
        # a name that ends in a backslash: trimming it would misreport the bytes
        assert path_rules.display_name("/uploads/notes\\") == "notes\\"

    def test_windows_trims_both_separators(self, as_windows):
        assert path_rules.display_name(r"C:\uploads\notes.txt") == "notes.txt"
        assert path_rules.display_name("C:\\uploads\\notes.txt\\\\") == "notes.txt"
        assert path_rules.display_name("C:/uploads/notes.txt") == "notes.txt"


class TestContainment:
    def test_a_root_that_ends_in_a_separator_still_matches(self, as_posix):
        assert path_rules._is_within("/uploads/a/f.txt", "/uploads/")
        assert path_rules._is_within("/uploads", "/uploads")

    def test_a_sibling_prefix_is_not_inside(self, as_posix):
        assert not path_rules._is_within("/uploads-private/f.txt", "/uploads")

    def test_the_filesystem_root_matches_its_children(self, as_posix):
        assert path_rules._is_within("/etc/passwd", "/")

    def test_unc_containment_is_case_insensitive(self, as_windows):
        assert path_rules._is_within_unc(
            r"\\FILESERV\Reports\q3.xlsx", r"\\fileserv\reports"
        )

    def test_unc_sibling_prefix_is_not_inside(self, as_windows):
        assert not path_rules._is_within_unc(
            r"\\fileserv\reports-private\f.txt", r"\\fileserv\reports"
        )


class TestNoThirdPartyImports:
    def test_the_cli_can_use_these_rules_without_discord(self):
        # scripts/dcli.py ships in the npm package separately from the Python one,
        # so importing this module must not pull in discord.py
        import sys

        source = pathlib.Path(path_rules.__file__).read_text(encoding="utf-8")
        imported = {
            line.split()[1]
            for line in source.splitlines()
            if line.startswith("import ") and len(line.split()) > 1
        }
        assert imported <= set(sys.stdlib_module_names), imported

    def test_the_cli_validates_paths_without_importing_discord(self, tmp_path):
        # the real failure mode: a newer CLI script paired with a Python package
        # that cannot import discord.py. Validating a path, and every command that
        # does not send a file, must still work
        import subprocess
        import sys

        blocker = tmp_path / "discord.py"
        blocker.write_text("raise ImportError('discord.py is not installed')\n")
        dcli = pathlib.Path(path_rules.__file__).parent.parent / "scripts" / "dcli.py"

        result = subprocess.run(
            [sys.executable, str(dcli), "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(tmp_path)},
        )
        assert result.returncode == 0, result.stderr
        assert "send-message" in result.stdout


class TestWindowsRulesDoNotFollowTheHost:
    """The Windows rules stay Windows-shaped whatever the host module is.

    ``_pathmod`` exists so host-dependent behaviour (``isabs``, ``basename``) can
    be switched. The Windows-only rules must not read it, because on the Linux
    runner they are reached only when something has asked for Windows behaviour,
    and there the host module is the wrong one to consult.
    """

    @pytest.fixture
    def windows_on_posix_module(self, monkeypatch):
        monkeypatch.setattr(path_rules, "ON_WINDOWS", True)
        monkeypatch.setattr(path_rules, "_pathmod", posixpath)

    @pytest.mark.parametrize("path", ["\\notes.txt", "D:notes.txt", "/notes.txt"])
    def test_drive_relative_paths_are_still_refused(
        self, windows_on_posix_module, path
    ):
        error = path_rules.path_shape_error(path)
        assert error is not None
        assert "not fully qualified" in error

    def test_a_qualified_windows_path_passes_the_windows_rules(
        self, windows_on_posix_module
    ):
        # isabs is deliberately host-switchable, so only the Windows-only rules are
        # in scope here: a fully qualified path must not be refused as ambiguous
        assert (
            path_rules.path_qualification_error(r"C:\uploads\f.txt") is None
        )

    def test_unc_containment_is_still_windows_shaped(self, windows_on_posix_module):
        # posixpath.normcase folds nothing and posixpath.sep is "/", so a host
        # module here would let a sibling share through and reject a real child
        assert path_rules.check_unc_confinement(
            r"\\FILESERV\Reports\q3.xlsx", [r"\\fileserv\reports"]
        ) is None
        assert (
            path_rules.check_unc_confinement(
                r"\\fileserv\reports-private\f.txt", [r"\\fileserv\reports"]
            )
            is not None
        )
