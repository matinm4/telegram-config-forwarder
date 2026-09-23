"""Unit tests for Bot API sender with fake HTTP (T020)."""
import json

import httpx
import pytest

from src.models import Destination
from src.providers.bot_sender import BotApiSender


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _dest():
    return Destination(id="main", chat="@testdest", enabled=True,
                       sender="bot_api", quarantine=False)


async def test_success():
    def ok(request):
        return httpx.Response(200, json={"ok": True,
                                         "result": {"message_id": 7}})

    sender = BotApiSender("T", client=_client(ok))  # noqa: S105
    res = await sender.send(_dest(), "hello")
    assert res.ok and res.message_id == "7" and res.error_class is None


async def test_rate_limit_is_retryable():
    def limited(request):
        return httpx.Response(429, json={"ok": False})

    sender = BotApiSender("T", client=_client(limited))  # noqa: S105
    res = await sender.send(_dest(), "hello")
    assert res.ok is False and res.error_class == "retryable"


async def test_bad_chat_is_permanent():
    def bad(request):
        return httpx.Response(400, json={"ok": False,
                                         "description": "bad request"})

    sender = BotApiSender("T", client=_client(bad))  # noqa: S105
    res = await sender.send(_dest(), "hello")
    assert res.ok is False and res.error_class == "permanent"


async def test_timeout_is_retryable():
    def slow(request):
        raise httpx.ConnectTimeout("slow")

    sender = BotApiSender("T", client=_client(slow))  # noqa: S105
    res = await sender.send(_dest(), "hello")
    assert res.ok is False and res.error_class == "retryable"
