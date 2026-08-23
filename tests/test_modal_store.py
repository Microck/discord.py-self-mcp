import pytest

from discord_py_self_mcp import modal_store


class FakeModal:
    def __init__(self, custom_id):
        self.custom_id = custom_id


@pytest.fixture(autouse=True)
def clean_store():
    modal_store.clear()
    yield
    modal_store.clear()


def test_put_then_take_returns_modal():
    modal = FakeModal("auth_profile:ABC")
    modal_store.put(modal)
    assert modal_store.take("auth_profile:ABC") is modal


def test_take_removes_the_entry():
    modal_store.put(FakeModal("auth_profile:ABC"))
    modal_store.take("auth_profile:ABC")
    assert modal_store.take("auth_profile:ABC") is None


def test_take_unknown_id_returns_none():
    assert modal_store.take("nope") is None


def test_put_same_id_twice_keeps_the_newest():
    old = FakeModal("dup")
    new = FakeModal("dup")
    modal_store.put(old)
    modal_store.put(new)
    assert modal_store.take("dup") is new


def test_evicts_oldest_beyond_the_cap():
    for i in range(modal_store.MAX_PENDING_MODALS + 1):
        modal_store.put(FakeModal(f"id-{i}"))
    assert modal_store.take("id-0") is None
    assert modal_store.take("id-1") is not None


def test_known_ids_lists_pending_modals():
    modal_store.put(FakeModal("a"))
    modal_store.put(FakeModal("b"))
    assert sorted(modal_store.known_ids()) == ["a", "b"]
