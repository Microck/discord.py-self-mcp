import pytest

from discord_py_self_mcp import main


@pytest.mark.asyncio
async def test_run_app_exits_with_actionable_error_when_token_missing(
    monkeypatch, capsys
):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)

    with pytest.raises(SystemExit) as exc:
        await main.run_app()

    assert exc.value.code == 1
    assert "DISCORD_TOKEN is not set" in capsys.readouterr().err
