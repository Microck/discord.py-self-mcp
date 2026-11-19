import asyncio
import io
import ntpath
import os
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discord_py_self_mcp import file_utils, path_rules


@pytest.fixture(autouse=True)
def uploads_enabled(tmp_path, monkeypatch):
    """Uploads are refused unless the operator names a directory, so most tests
    need one. Tests that exercise the gate itself override this."""
    root = tmp_path / "uploads"
    root.mkdir(exist_ok=True)
    monkeypatch.setenv("UPLOAD_DIRS", str(root))
    return root


def make_file(directory, name="report.xlsx", content=b"hello"):
    path = directory / name
    path.write_bytes(content)
    return str(path)


@pytest.fixture
def upload_dir(uploads_enabled):
    return uploads_enabled


class TestNormalizeFilePaths:
    def test_none_becomes_empty_list(self):
        assert file_utils.normalize_file_paths(None) == []

    def test_single_string_is_wrapped(self, upload_dir):
        path = make_file(upload_dir)
        assert file_utils.normalize_file_paths(path) == [path]

    def test_list_is_preserved(self, upload_dir):
        paths = [make_file(upload_dir, "a.txt"), make_file(upload_dir, "b.txt")]
        assert file_utils.normalize_file_paths(paths) == paths

    def test_paths_are_not_stripped(self, upload_dir):
        # a trailing space is a legal POSIX filename; rewriting it could select a
        # different file than the caller asked for
        path = make_file(upload_dir, "report .txt")
        assert file_utils.normalize_file_paths([path]) == [path]

    def test_blank_entries_are_kept_so_they_can_be_rejected(self):
        assert file_utils.normalize_file_paths(["a.txt", ""]) == ["a.txt", ""]

    @pytest.mark.parametrize("bad", [123, b"bytes", 1.5, object()])
    def test_non_string_entries_are_rejected(self, bad):
        with pytest.raises(ValueError):
            file_utils.normalize_file_paths([bad])

    def test_bytes_input_is_rejected(self):
        with pytest.raises(ValueError):
            file_utils.normalize_file_paths(b"/tmp/x.txt")

    def test_arbitrary_iterable_is_rejected(self):
        with pytest.raises(ValueError):
            file_utils.normalize_file_paths({"a.txt"})


class TestUploadDirsGate:
    def test_unset_upload_dirs_refuses_uploads(self, monkeypatch, upload_dir):
        monkeypatch.delenv("UPLOAD_DIRS", raising=False)
        path = make_file(upload_dir)
        error = file_utils.validate_file_paths([path])
        assert error is not None
        assert "uploads are not enabled" in error.lower()
        assert "UPLOAD_DIRS" in error

    @pytest.mark.parametrize("raw", ["", "   ", os.pathsep, f"{os.pathsep}{os.pathsep}"])
    def test_blank_upload_dirs_does_not_open_the_door(self, monkeypatch, upload_dir, raw):
        monkeypatch.setenv("UPLOAD_DIRS", raw)
        path = make_file(upload_dir)
        error = file_utils.validate_file_paths([path])
        assert error is not None
        assert "UPLOAD_DIRS" in error

    def test_upload_dirs_pointing_nowhere_refuses_uploads(self, monkeypatch, tmp_path):
        monkeypatch.setenv("UPLOAD_DIRS", str(tmp_path / "does-not-exist"))
        path = make_file(tmp_path, "x.txt")
        error = file_utils.validate_file_paths([path])
        assert "no existing directory" in error

    def test_text_sends_still_work_without_upload_dirs(self, monkeypatch):
        monkeypatch.delenv("UPLOAD_DIRS", raising=False)
        assert file_utils.validate_file_paths(None) is None
        assert file_utils.validate_file_paths([]) is None


class TestValidateFilePaths:
    def test_existing_file_passes(self, upload_dir):
        assert file_utils.validate_file_paths([make_file(upload_dir)]) is None

    def test_missing_file_is_reported(self, upload_dir):
        missing = str(upload_dir / "nope.bin")
        assert file_utils.validate_file_paths([missing]) == f"File not found: {missing}"

    def test_directory_is_rejected(self, upload_dir):
        assert file_utils.validate_file_paths([str(upload_dir)]) == (
            f"Not a file: {upload_dir}"
        )

    def test_empty_path_is_reported(self):
        assert file_utils.validate_file_paths([""]) == (
            "file_paths contains an empty path"
        )

    def test_relative_path_is_rejected(self):
        error = file_utils.validate_file_paths(["notes.txt"])
        assert error == "file_paths must be absolute, got: notes.txt"

    def test_too_many_files_is_reported(self, upload_dir):
        paths = [make_file(upload_dir, f"f{i}.bin") for i in range(11)]
        error = file_utils.validate_file_paths(paths)
        assert error.startswith("Too many files")
        assert "10 attachments per message" in error

    def test_oversized_file_is_reported(self, upload_dir, monkeypatch):
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "4")
        path = make_file(upload_dir, content=b"way too long")
        error = file_utils.validate_file_paths([path])
        assert "above the 4 byte limit" in error
        assert "MAX_UPLOAD_BYTES" in error

    def test_size_limit_override_is_honoured(self, upload_dir, monkeypatch):
        # a 5-byte file must pass at 5 and fail at 4, proving the override is used
        path = make_file(upload_dir, content=b"12345")
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "5")
        assert file_utils.validate_file_paths([path]) is None
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "4")
        assert "above the 4 byte limit" in file_utils.validate_file_paths([path])

    def test_combined_total_is_capped(self, upload_dir, monkeypatch):
        # 4 + 4 bytes against a 7 byte combined budget
        monkeypatch.setenv("MAX_UPLOAD_TOTAL_BYTES", "7")
        paths = [
            make_file(upload_dir, "a.bin", b"1234"),
            make_file(upload_dir, "b.bin", b"5678"),
        ]
        error = file_utils.validate_file_paths(paths)
        assert "combined limit" in error
        assert "MAX_UPLOAD_TOTAL_BYTES" in error

    def test_combined_total_exactly_at_the_limit_passes(self, upload_dir, monkeypatch):
        monkeypatch.setenv("MAX_UPLOAD_TOTAL_BYTES", "8")
        paths = [
            make_file(upload_dir, "a.bin", b"1234"),
            make_file(upload_dir, "b.bin", b"5678"),
        ]
        assert file_utils.validate_file_paths(paths) is None

    @pytest.mark.parametrize("raw", ["", "not-a-number", "0", "-5"])
    def test_bad_limit_falls_back_to_default(self, raw, monkeypatch):
        monkeypatch.setenv("MAX_UPLOAD_BYTES", raw)
        assert file_utils.max_upload_bytes() == file_utils.MAX_UPLOAD_BYTES_DEFAULT


class TestContainment:
    def test_file_inside_allowed_root_passes(self, upload_dir):
        assert file_utils.validate_file_paths([make_file(upload_dir)]) is None

    def test_file_outside_allowed_root_is_rejected(self, tmp_path, uploads_enabled):
        path = make_file(tmp_path)
        refusal = file_utils.validate_file_paths([path])
        assert "outside the directories" in refusal
        os.unlink(path)
        assert file_utils.validate_file_paths([path]) == refusal

    @pytest.mark.skipif(os.name != "nt", reason="Windows drive-qualified names")
    def test_missing_diagnostic_skips_drive_qualified_leaf(self, upload_dir, monkeypatch):
        def unexpected_lookup(*args, **kwargs):
            pytest.fail("a drive-qualified leaf was used for a missing-file lookup")

        with monkeypatch.context() as patch:
            patch.setattr(file_utils, "_realpath", unexpected_lookup)
            patch.setattr(os, "lstat", unexpected_lookup)
            path = str(upload_dir) + "\\D:report.txt"
            assert not file_utils._missing_in_upload_dir(path, [str(upload_dir)])

    def test_dotdot_traversal_is_rejected(self, tmp_path, uploads_enabled):
        # the ".." must reach production un-normalised, otherwise the test proves
        # nothing about the code under test
        make_file(tmp_path, "secret.txt")
        traversal = str(uploads_enabled / ".." / "secret.txt")
        assert ".." in traversal

        error = file_utils.validate_file_paths([traversal])
        assert error is not None
        assert "outside the directories" in error

    def test_sibling_prefix_is_not_treated_as_inside(self, tmp_path, uploads_enabled):
        sibling = tmp_path / "uploads-private"
        sibling.mkdir()
        path = make_file(sibling)
        assert "outside the directories" in file_utils.validate_file_paths([path])

    def test_symlink_escape_is_rejected(self, uploads_enabled, tmp_path):
        secret = make_file(tmp_path, "secret.txt")
        link = uploads_enabled / "innocent.txt"
        try:
            os.symlink(secret, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable on this platform")
        assert "outside the directories" in file_utils.validate_file_paths([str(link)])

    def test_allowed_root_itself_is_within_itself(self, uploads_enabled):
        # regression: a root ending in a separator used to reject its own children
        assert path_rules._is_within(
            os.path.realpath(str(uploads_enabled)),
            os.path.realpath(str(uploads_enabled)),
        )

    def test_root_with_trailing_separator_still_matches_children(self, uploads_enabled):
        root = os.path.realpath(str(uploads_enabled)) + os.sep
        child = os.path.realpath(make_file(uploads_enabled))
        assert path_rules._is_within(child, root)

    def test_filesystem_root_allows_children(self):
        if os.name == "nt":
            root = os.path.abspath(os.sep)  # e.g. "C:\\", which ends in a separator
            assert path_rules._is_within(os.path.join(root, "a", "b.txt"), root)
        else:
            assert path_rules._is_within("/etc/passwd", "/")

    def test_case_variant_of_an_allowed_file_is_accepted(self, upload_dir):
        path = make_file(upload_dir, "MixedCase.txt")
        variant = path.replace("MixedCase.txt", "mixedcase.txt")
        # whether that is the same file is a property of the filesystem, so ask it
        # rather than inferring the answer from normcase(), which folds case on
        # Windows even for a case-sensitive directory and not on POSIX even for a
        # case-insensitive one
        same_file = os.path.exists(variant)

        error = file_utils.validate_file_paths([variant])

        if same_file:
            # the variant is the same file, so it must still be allowed
            assert error is None
        else:
            # a different file that does not exist: refused, not silently skipped
            assert "File not found" in error


@pytest.mark.asyncio
async def test_slow_upload_io_allows_event_loop_to_run(monkeypatch, upload_dir):
    loop = asyncio.get_running_loop()
    steps = []
    path = make_file(upload_dir)

    def heartbeat(name):
        steps.append(name)
        ready = threading.Event()
        loop.call_soon_threadsafe(ready.set)
        assert ready.wait(timeout=3), f"event loop blocked during {name}"

    validate = file_utils.validate_file_paths

    def slow_validate(paths):
        heartbeat("validate")
        return validate(paths)

    def slow_open(*args, **kwargs):
        heartbeat("read")
        return io.open(*args, **kwargs)

    async def rate_limit(action):
        assert asyncio.get_running_loop() is loop
        steps.append(action)

    channel = SimpleNamespace(send=AsyncMock())
    monkeypatch.setattr(file_utils, "validate_file_paths", slow_validate)
    monkeypatch.setattr(file_utils, "open", slow_open, raising=False)
    await file_utils.send_with_files(channel, "caption", [path], {}, rate_limit)
    channel.send.assert_awaited_once()
    assert steps == ["validate", "read", "message"]


@pytest.mark.asyncio
async def test_concurrent_uploads_take_the_rate_slot_at_send(monkeypatch, upload_dir):
    from discord_py_self_mcp.rate_limiter import RateLimitConfig, RateLimiter

    limiter = RateLimiter(RateLimitConfig(messages_per_second=1))
    loop = asyncio.get_running_loop()
    slow = make_file(upload_dir, "slow.txt")
    fast = make_file(upload_dir, "fast.txt")
    reading = asyncio.Event()
    release = threading.Event()
    sends = []

    def delayed_open(path, mode, **kwargs):
        if path == slow:
            loop.call_soon_threadsafe(reading.set)
            assert release.wait(5)
        return io.open(path, mode, **kwargs)

    async def send(content, **kwargs):
        sends.append((content, loop.time()))
        release.set()

    channel = SimpleNamespace(send=send)
    monkeypatch.setattr(file_utils, "open", delayed_open, raising=False)
    first = asyncio.create_task(
        file_utils.send_with_files(channel, "slow", [slow], {}, limiter.wait_if_needed)
    )
    try:
        await asyncio.wait_for(reading.wait(), 5)
        await file_utils.send_with_files(channel, "fast", [fast], {}, limiter.wait_if_needed)
    finally:
        release.set()
        await first
    assert [caption for caption, _ in sends] == ["fast", "slow"]
    assert sends[1][1] - sends[0][1] >= 0.95


def test_relative_roots_never_grant_the_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UPLOAD_DIRS", ".")
    assert file_utils._upload_roots() == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX directory names")
def test_root_with_trailing_space_is_distinct(monkeypatch, tmp_path):
    allowed = tmp_path / "reports "
    allowed.mkdir()
    sibling = tmp_path / "reports"
    sibling.mkdir()
    monkeypatch.setenv("UPLOAD_DIRS", str(allowed))
    assert file_utils.validate_file_paths([make_file(allowed)]) is None
    assert "outside the directories" in file_utils.validate_file_paths([make_file(sibling)])


def test_incomplete_resolution_refuses_to_open(monkeypatch, upload_dir):
    path = make_file(upload_dir)
    resolve = file_utils._realpath

    def failing_resolution(candidate, *, strict):
        assert strict
        if candidate == path:
            raise PermissionError("lookup failed")
        return resolve(candidate, strict=strict)

    monkeypatch.setattr(file_utils, "_realpath", failing_resolution)
    monkeypatch.setattr(file_utils, "open", lambda *args: pytest.fail("opened"), raising=False)
    files, error = file_utils.build_files([path])
    assert not files and "unavailable or outside the directories" in error


class TestBuildFiles:
    @pytest.mark.skipif(not hasattr(os, "O_NONBLOCK"), reason="POSIX open flags")
    def test_opens_nonblocking_before_checking_file_type(self, monkeypatch, upload_dir):
        path = make_file(upload_dir)
        original = os.open
        flags_seen = []

        def record_open(name, flags):
            flags_seen.append(flags)
            return original(name, flags)

        with monkeypatch.context() as patch:
            patch.setattr(os, "open", record_open)
            files, error = file_utils.build_files([path])
        assert error is None and files
        assert len(flags_seen) == 1 and flags_seen[0] & os.O_NONBLOCK

    def test_no_paths_returns_no_files_and_no_error(self):
        files, error = file_utils.build_files(None)
        assert files == []
        assert error is None

    def test_file_is_read_into_memory(self, upload_dir):
        path = make_file(upload_dir, "sheet.xlsx", content=b"the-bytes")
        files, error = file_utils.build_files([path])

        assert error is None
        assert len(files) == 1
        assert files[0].filename == "sheet.xlsx"
        assert files[0].fp.read() == b"the-bytes"

    def test_single_string_is_accepted(self, upload_dir):
        files, error = file_utils.build_files(make_file(upload_dir))
        assert error is None
        assert len(files) == 1

    def test_bad_path_loads_nothing(self, upload_dir):
        files, error = file_utils.build_files(
            [make_file(upload_dir), str(upload_dir / "missing.txt")]
        )
        assert files == []
        assert "File not found" in error

    def test_read_is_bounded_by_the_configured_limit(self, upload_dir, monkeypatch):
        # the limit has to be enforced by the read itself, not by measuring what an
        # unbounded read returned, or a file that grew after validation could be
        # slurped into memory before being rejected
        path = make_file(upload_dir, content=b"tiny")
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "64")

        requested = []

        real_open = io.open

        class RecordingReader:
            def __init__(self, inner):
                self._inner = inner

            def read(self, size=-1):
                requested.append(size)
                return self._inner.read(size)

            def fileno(self):
                return self._inner.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._inner.close()

        def recording_open(f, *a, **kw):
            return RecordingReader(real_open(f, *a, **kw))

        monkeypatch.setattr(file_utils, "open", recording_open, raising=False)
        files, error = file_utils.build_files([path])

        assert error is None
        # one byte past the cap is enough to detect an oversized file without
        # buffering all of it
        assert requested == [65]
        assert len(files) == 1

    def test_growth_past_the_limit_is_caught_even_after_validation(
        self, upload_dir, monkeypatch
    ):
        path = make_file(upload_dir, content=b"tiny")
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "64")

        real_open = io.open

        class GrowingReader:
            def __init__(self, inner):
                self._inner = inner

            def read(self, size=-1):
                # pretend the file grew after the pre-flight stat
                return b"x" * 5000 if size in (None, -1) else (b"x" * 5000)[:size]

            def fileno(self):
                return self._inner.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._inner.close()

        def growing_open(f, *a, **kw):
            return GrowingReader(real_open(f, *a, **kw))

        monkeypatch.setattr(file_utils, "open", growing_open, raising=False)
        files, error = file_utils.build_files([path])

        assert files == []
        assert "larger than 64 bytes once read" in error

    def test_later_files_are_read_against_the_remaining_total(self, upload_dir, monkeypatch):
        # the per-file cap is generous, so only the combined budget can stop the
        # second read. Reading "per_file + 1" here would buffer a file the message
        # cannot carry before rejecting it
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "1000")
        monkeypatch.setenv("MAX_UPLOAD_TOTAL_BYTES", "8")
        paths = [
            make_file(upload_dir, "a.bin", b"1234"),
            make_file(upload_dir, "b.bin", b"5678"),
        ]

        requested = []
        real_open = io.open

        class RecordingReader:
            def __init__(self, inner):
                self._inner = inner

            def read(self, size=-1):
                requested.append(size)
                return self._inner.read(size)

            def fileno(self):
                return self._inner.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._inner.close()

        def recording_open(f, *a, **kw):
            return RecordingReader(real_open(f, *a, **kw))

        monkeypatch.setattr(file_utils, "open", recording_open, raising=False)
        files, error = file_utils.build_files(paths)

        assert error is None
        assert len(files) == 2
        # the first read may use the whole combined budget (8 + 1 to detect an
        # overrun); once 4 bytes are in, the second is capped at what is left
        assert requested == [9, 5]

    def test_combined_total_is_enforced_at_read_time(self, upload_dir, monkeypatch):
        # the pre-flight stat can be stale, so the read itself has to catch a total
        # that grew past the combined limit
        monkeypatch.setenv("MAX_UPLOAD_BYTES", "1000")
        monkeypatch.setenv("MAX_UPLOAD_TOTAL_BYTES", "8")
        paths = [
            make_file(upload_dir, "a.bin", b"1234"),
            make_file(upload_dir, "b.bin", b"5678"),
        ]

        real_open = io.open

        class GrowingReader:
            def __init__(self, inner, name):
                self._inner = inner
                self._name = name

            def read(self, size=-1):
                # the second file pretends to have grown since validation
                payload = b"1234567890" if self._name.endswith("b.bin") else b"1234"
                return payload if size in (None, -1) else payload[:size]

            def fileno(self):
                return self._inner.fileno()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._inner.close()

        def growing_open(f, *a, **kw):
            return GrowingReader(real_open(f, *a, **kw), str(f))

        monkeypatch.setattr(file_utils, "open", growing_open, raising=False)
        files, error = file_utils.build_files(paths)

        assert files == []
        assert "more than 8 bytes" in error

    def test_relative_path_is_rejected_before_read(self, upload_dir, monkeypatch):
        monkeypatch.chdir(upload_dir)
        (upload_dir / "here.txt").write_bytes(b"x")
        files, error = file_utils.build_files(["here.txt"])
        assert files == []
        assert error.startswith("file_paths must be absolute")

    def test_regular_file_predicate_accepts_a_real_file(self, upload_dir):
        path = make_file(upload_dir)
        with open(path, "rb") as handle:
            assert file_utils._is_regular(handle) is True

    def test_regular_file_predicate_rejects_a_pipe(self):
        # a real non-regular descriptor, so the production predicate is what fails
        read_fd, write_fd = os.pipe()
        try:
            with io.open(read_fd, "rb", closefd=False) as handle:
                assert file_utils._is_regular(handle) is False
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_build_files_refuses_a_non_regular_file(self, upload_dir, monkeypatch):
        # wiring only: that a refusal from the predicate stops the send. The
        # predicate itself is covered against real descriptors above
        path = make_file(upload_dir)
        monkeypatch.setattr(file_utils, "_is_regular", lambda handle: False)

        files, error = file_utils.build_files([path])

        assert files == []
        assert "Not a regular file" in error

    def test_spoiler_prefix_is_carried_through(self, upload_dir):
        # runs everywhere: build_files must hand the caller's basename to
        # discord.File, which derives spoiler handling from it
        path = make_file(upload_dir, "SPOILER_report.pdf", content=b"pdf")
        files, error = file_utils.build_files([path])

        assert error is None
        assert files[0].filename == "SPOILER_report.pdf"
        assert files[0].spoiler is True

    def test_spoiler_link_keeps_its_display_name(self, upload_dir):
        # discord.File derives both the display name and spoiler handling from the
        # filename, so using the resolved basename would rename the attachment and
        # silently drop the spoiler flag
        target = make_file(upload_dir, "report.pdf", content=b"pdf")
        link = upload_dir / "SPOILER_report.pdf"
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable on this platform")

        files, error = file_utils.build_files([str(link)])

        assert error is None
        assert files[0].filename == "SPOILER_report.pdf"
        assert files[0].spoiler is True

    def test_trailing_separator_never_yields_an_empty_filename(self, upload_dir):
        # Windows normalises a trailing separator away and POSIX treats it as a
        # directory, so the two platforms differ; what must hold on both is that we
        # either refuse or send a real name, never a blank one
        path = make_file(upload_dir, "notes.txt", content=b"x")
        files, error = file_utils.build_files([path + os.sep])

        if error is None:
            assert [f.filename for f in files] == ["notes.txt"]
        else:
            assert files == []

    def test_bytes_are_uploaded_exactly_as_read(self, upload_dir):
        payload = bytes(range(256))
        path = make_file(upload_dir, "bytes.bin", content=payload)
        files, _ = file_utils.build_files([path])
        assert files[0].fp.read() == payload

    def test_a_read_failure_reports_the_requested_path_not_the_target(
        self, upload_dir
    ):
        # the file is opened by its resolved path, which may sit behind a link the
        # caller has no business learning about; the error must name what they
        # asked for and the reason, without the target's filename
        target = make_file(upload_dir, "hidden-target.bin", content=b"x")
        link = upload_dir / "public.txt"
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable on this platform")

        real_open = io.open

        def failing_open(f, *a, **kw):
            handle = real_open(f, *a, **kw)
            handle.close()
            raise PermissionError(13, "Permission denied", f)

        import unittest.mock as mock

        with mock.patch.object(file_utils, "open", failing_open, create=True):
            files, error = file_utils.build_files([str(link)])

        assert files == []
        assert "public.txt" in error
        assert "hidden-target" not in error

    def test_a_read_failure_omits_the_resolved_path_without_a_symlink(
        self, upload_dir, monkeypatch
    ):
        # the same property without needing symlink privileges, so it holds on the
        # Windows dev box as well as on CI: the resolved path handed to open() must
        # never reach the message
        path = make_file(upload_dir, "public.txt", content=b"x")
        monkeypatch.setattr(
            file_utils,
            "_resolve_for_upload",
            lambda p, roots: (r"/somewhere/private/hidden-target.bin", None),
        )

        def failing_open(f, *a, **kw):
            raise PermissionError(13, "Permission denied", f)

        monkeypatch.setattr(file_utils, "open", failing_open, raising=False)
        files, error = file_utils.build_files([path])

        assert files == []
        assert "public.txt" in error
        assert "hidden-target" not in error
        assert "Permission denied" in error

    @pytest.mark.skipif(os.name == "nt", reason="POSIX filename semantics")
    def test_a_backslash_in_a_posix_filename_survives_a_real_send(self, upload_dir):
        # end to end, not just the helper: a POSIX file whose name contains a
        # backslash must keep that name on the attachment
        path = make_file(upload_dir, "notes\\2026", content=b"x")
        files, error = file_utils.build_files([path])

        assert error is None
        assert files[0].filename == "notes\\2026"


class TestFormatFileSummary:
    class Handle:
        def __init__(self, filename):
            self.filename = filename

    def test_no_files_yields_empty_string(self):
        assert file_utils.format_file_summary([]) == ""
        assert file_utils.format_file_summary(None) == ""

    def test_single_attachment_is_singular(self):
        assert file_utils.format_file_summary([self.Handle("a.png")]) == (
            " with 1 attachment: a.png"
        )

    def test_multiple_attachments_are_plural(self):
        summary = file_utils.format_file_summary(
            [self.Handle("a.png"), self.Handle("b.pdf")]
        )
        assert summary == " with 2 attachments: a.png, b.pdf"

    def test_handle_without_filename_falls_back(self):
        assert file_utils.format_file_summary([object()]) == (
            " with 1 attachment: attachment"
        )


class TestSentSummary:
    class Handle:
        def __init__(self, filename):
            self.filename = filename

    class Message:
        def __init__(self, attachments):
            self.attachments = attachments

    def test_reports_the_name_discord_kept(self):
        # Discord renames a file that collides with one already on the message, so
        # the name on the returned message is the one the caller can refer to
        message = self.Message([self.Handle("report (1).xlsx")])
        sent = [self.Handle("report.xlsx")]
        assert file_utils.format_sent_summary(message, sent) == (
            " with 1 attachment: report (1).xlsx"
        )

    def test_falls_back_when_the_message_lists_no_attachments(self):
        message = self.Message(None)
        sent = [self.Handle("report.xlsx")]
        assert file_utils.format_sent_summary(message, sent) == (
            " with 1 attachment: report.xlsx"
        )

    def test_no_files_yields_empty_string(self):
        assert file_utils.format_sent_summary(self.Message([]), []) == ""

    def test_reports_when_discord_returned_no_attachments(self):
        assert file_utils.format_sent_summary(self.Message([]), [self.Handle("a.png")]) == (
            " (Discord reported no attachments)"
        )


class TestRemovedInternals:
    def test_the_lexical_rules_no_longer_live_here(self):
        # they moved to path_rules so the CLI can use them without importing
        # discord.py; keeping a second copy here would let the two drift
        for name in (
            "_is_within",
            "_is_unc_path",
            "_display_name",
            "path_shape_error",
            "path_qualification_error",
        ):
            assert not hasattr(file_utils, name), name


class TestUncIntegration:
    """The network rules wired into the real validation path.

    The lexical decisions themselves live in test_path_rules.py; what matters here
    is that validation reaches them before anything can contact a server.
    os.path.realpath() on a UNC path was measured blocking for 47 seconds on a
    routable but dead address, which one tool request is enough to trigger.
    """

    SHARE = "\\\\fileserv\\reports"

    @pytest.fixture
    def windows_rules(self, monkeypatch):
        """Evaluate the rules as a Windows host would, on any platform.

        UNC paths have no POSIX meaning, so these assertions are only about the
        Windows branch. Turning the branch on rather than skipping off keeps the
        checks running on the Linux runner that the CI uses.
        """
        monkeypatch.setattr(path_rules, "ON_WINDOWS", True)
        monkeypatch.setattr(path_rules, "_pathmod", ntpath)

    @pytest.fixture
    def no_resolution(self, monkeypatch):
        """Any resolution attempt is a failure, not merely a slow call."""

        def never(path):
            raise AssertionError(f"must not resolve a network path: {path}")

        monkeypatch.setattr(file_utils, "_realpath", never)

    def test_resolve_helper_returns_the_share_as_written(self, windows_rules, no_resolution):
        target = self.SHARE + "\\q3.xlsx"
        resolved, error = file_utils._resolve_for_upload(target, [self.SHARE])
        assert error is None
        assert resolved == target

    def test_a_mixed_separator_share_is_not_resolved(self, monkeypatch, no_resolution):
        # Windows reads a mixed leading pair as UNC too, so it must be caught by
        # the same branch rather than falling through to the local resolver
        monkeypatch.setattr(path_rules, "ON_WINDOWS", True)
        error = file_utils._resolve_for_upload(
            "\\/fileserv\\reports\\q3.xlsx", [self.SHARE]
        )[1]
        assert error is None or "outside the directories" in error

    def test_configured_share_is_kept_as_written(self, monkeypatch, windows_rules, no_resolution):
        monkeypatch.setenv("UPLOAD_DIRS", self.SHARE)
        assert file_utils._upload_roots() == [self.SHARE]

    @pytest.mark.parametrize("component", ["..", ".. ", "reports.", "reports "])
    def test_ambiguous_share_root_is_dropped(self, monkeypatch, windows_rules, no_resolution, component):
        monkeypatch.setenv("UPLOAD_DIRS", self.SHARE + "\\" + component + "\\reports")
        assert file_utils._upload_roots() == []

    def test_a_bare_server_is_not_accepted_as_a_root(self, monkeypatch, windows_rules, no_resolution):
        # it would authorise every share on that server
        monkeypatch.setenv("UPLOAD_DIRS", "\\\\fileserv")
        assert file_utils._upload_roots() == []

    @pytest.mark.skipif(os.name != "nt", reason="Windows path semantics")
    @pytest.mark.parametrize(
        "spelling",
        [
            "\\\\no-such-host-zzzq\\share\\file.txt",
            "\\/no-such-host-zzzq\\share\\file.txt",
            "/\\no-such-host-zzzq\\share\\file.txt",
            "//no-such-host-zzzq/share/file.txt",
        ],
    )
    def test_dead_host_does_not_block_validation(self, monkeypatch, tmp_path, spelling):
        # end to end on real Windows, every spelling Windows treats as UNC. The
        # ceiling is generous, but the behaviour it guards against took 47 seconds
        import time

        monkeypatch.setenv("UPLOAD_DIRS", str(tmp_path))
        started = time.monotonic()
        error = file_utils.validate_file_paths([spelling])
        elapsed = time.monotonic() - started

        assert error is not None, spelling
        assert "outside the directories" in error, spelling
        assert elapsed < 2, f"{spelling} took {elapsed:.1f}s, so a resolve happened"
