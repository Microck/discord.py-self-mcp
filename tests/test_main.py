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


def test_main_selects_streamable_http_transport(monkeypatch):
    selected = {}

    async def fake_http(host, port):
        selected["transport"] = "streamable-http"
        selected["host"] = host
        selected["port"] = port

    def fake_run(coroutine):
        selected["coroutine"] = coroutine
        with pytest.raises(StopIteration):
            coroutine.send(None)

    monkeypatch.setattr(main, "run_streamable_http", fake_http)
    monkeypatch.setattr(main.asyncio, "run", fake_run)
    monkeypatch.setattr(
        main.sys,
        "argv",
        ["discord-py-self-mcp", "--transport", "streamable-http", "--host", "127.0.0.2", "--port", "8999"],
    )

    main.main()

    assert selected["transport"] == "streamable-http"
    assert selected["host"] == "127.0.0.2"
    assert selected["port"] == 8999


def test_create_streamable_http_app_exposes_mcp_route():
    http_app = main.create_streamable_http_app()

    assert [route.path for route in http_app.routes] == ["/mcp"]
