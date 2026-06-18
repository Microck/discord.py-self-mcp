from pathlib import Path

import pytest

from discord_py_self_mcp.tools import discrawl


def test_default_discrawl_candidates_are_fork_only():
    candidates = discrawl._default_discrawl_candidates()

    assert len(candidates) == 1
    assert Path(candidates[0]).parts[-3:] == ("discrawl-self", "bin", "discrawl")
    assert discrawl.DEFAULT_DISCRAWL_BINARY not in candidates


def test_default_discrawl_binary_uses_sibling_fork_even_when_missing():
    resolved = discrawl._resolve_discrawl_binary({})

    assert Path(resolved).parts[-3:] == ("discrawl-self", "bin", "discrawl")


def test_explicit_literal_discrawl_is_still_allowed():
    assert discrawl._resolve_discrawl_binary({"binary": "discrawl"}) == "discrawl"


def test_explicit_absolute_discrawl_exe_is_accepted(tmp_path):
    target = tmp_path / "discrawl.exe"

    assert discrawl._resolve_discrawl_binary({"binary": str(target)}) == str(target)


def test_explicit_absolute_discrawl_without_extension_is_accepted(tmp_path):
    target = tmp_path / "discrawl"

    assert discrawl._resolve_discrawl_binary({"binary": str(target)}) == str(target)


def test_explicit_absolute_wrong_name_is_rejected(tmp_path):
    target = tmp_path / "notdiscrawl.exe"

    with pytest.raises(ValueError, match="must point to a discrawl executable"):
        discrawl._resolve_discrawl_binary({"binary": str(target)})


@pytest.mark.asyncio
async def test_run_discrawl_rejects_relative_binary_path():
    result = await discrawl.run_discrawl({"command": "status", "binary": "./discrawl"})

    assert (
        result[0].text
        == "binary must be the literal 'discrawl' or an absolute path to a discrawl executable"
    )


@pytest.mark.asyncio
async def test_missing_default_binary_points_to_microck_fork(monkeypatch):
    monkeypatch.setattr(discrawl, "_binary_exists", lambda _binary: False)

    result = await discrawl.run_discrawl({"command": "status"})

    assert "https://github.com/Microck/discrawl-self" in result[0].text
    assert "../discrawl-self/bin/discrawl" in result[0].text
