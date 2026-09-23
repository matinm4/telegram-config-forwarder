"""Unit tests for Telethon fallback sender (T051)."""
from src.models import Destination
from src.providers.base import SendResult
from src.providers.telethon_sender import TelethonSender


class FakeClient:
    def __init__(self, behavior="ok"):
        self.behavior = behavior
        self.connected = False

    async def connect(self):
        self.connected = True

    async def is_user_authorized(self):
        return self.behavior != "unauthorized"

    async def send_message(self, chat, message, **kwargs):
        if self.behavior == "flood":
            raise RuntimeError("FloodWaitError: wait 30")
        if self.behavior == "broken":
            raise RuntimeError("AuthKeyError: invalid key")

        class M:
            id = 9

        return M()

    async def disconnect(self):
        self.connected = False


def _dest():
    return Destination(id="main", chat="@testdest", enabled=True,
                       sender="telethon", quarantine=False)


def test_send_ok():
    import asyncio
    s = TelethonSender(1, "h", "sess", client=FakeClient())  # noqa: S105
    res = asyncio.run(s.send(_dest(), "hi"))
    assert res.ok and res.message_id == "9"


def test_flood_is_retryable():
    import asyncio
    s = TelethonSender(1, "h", "sess",
                       client=FakeClient("flood"))  # noqa: S105
    res = asyncio.run(s.send(_dest(), "hi"))
    assert res.ok is False and res.error_class == "retryable"


def test_bad_key_is_permanent():
    import asyncio
    s = TelethonSender(1, "h", "sess",
                       client=FakeClient("broken"))  # noqa: S105
    res = asyncio.run(s.send(_dest(), "hi"))
    assert res.ok is False and res.error_class == "permanent"


def test_unauthorized_is_permanent():
    import asyncio
    s = TelethonSender(1, "h", "sess",
                       client=FakeClient("unauthorized"))  # noqa: S105
    res = asyncio.run(s.send(_dest(), "hi"))
    assert res.ok is False and res.error_class == "permanent"
