import pytest

from discord_py_self_mcp.tools import discrawl


def test_default_discrawl_candidates_are_fork_only():
    candidates = discrawl._default_discrawl_candidates()

    assert len(candidates) == 1
    assert candidates[0].endswith("discrawl-self/bin/discrawl")
    assert discrawl.DEFAULT_DISCRAWL_BINARY not in candidates


def test_default_discrawl_binary_uses_sibling_fork_even_when_missing():
    resolved = discrawl._resolve_discrawl_binary({})

    assert resolved.endswith("discrawl-self/bin/discrawl")


def test_explicit_literal_discrawl_is_still_allowed():
    assert discrawl._resolve_discrawl_binary({"binary": "discrawl"}) == "discrawl"


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
