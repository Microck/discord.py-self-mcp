import pytest

from discord_py_self_mcp import bot, modal_store


class FakeModal:
    def __init__(self, custom_id="auth_profile:ABC", title="프로필"):
        self.custom_id = custom_id
        self.title = title


@pytest.fixture(autouse=True)
def clean_store():
    modal_store.clear()
    yield
    modal_store.clear()


@pytest.mark.asyncio
async def test_on_modal_stores_the_modal():
    modal = FakeModal()
    await bot.SelfBot.on_modal(None, modal)
    assert modal_store.take("auth_profile:ABC") is modal
