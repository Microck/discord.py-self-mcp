"""Short-lived store for modals pushed by Discord over the gateway.

A modal arrives on INTERACTION_MODAL_CREATE, separately from the button click
that triggered it. Holding it here lets `submit_modal` answer and submit it
without clicking the button a second time.
"""

from collections import OrderedDict

# A user account has one modal open at a time in practice, and interactions
# expire after roughly 15 minutes. The cap only stops a long QA session from
# growing the dict without bound.
MAX_PENDING_MODALS = 16

_pending: "OrderedDict[str, object]" = OrderedDict()


def put(modal) -> None:
    custom_id = modal.custom_id
    if custom_id in _pending:
        del _pending[custom_id]
    _pending[custom_id] = modal
    while len(_pending) > MAX_PENDING_MODALS:
        _pending.popitem(last=False)


def take(custom_id: str):
    return _pending.pop(custom_id, None)


def known_ids() -> list[str]:
    return list(_pending)


def clear() -> None:
    _pending.clear()
