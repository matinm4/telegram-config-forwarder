"""Integration tests for the MVP pipeline incl. idempotency (T021)."""
import asyncio
import os

import httpx
import yaml

from src.config_loader import load_config
from src.persistence.state_store import StateStore
from src.pipeline import run_once
from src.providers.base import SendResult
from src.providers.scrape_source import ScrapeSourceProvider

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures")


class FakeSender:
    name = "fake"

    def __init__(self):
        self.sent = []

    async def send(self, destination, body):
        self.sent.append((destination.id, body))
        return SendResult(ok=True, message_id=str(len(self.sent)))


def _mock_client():
    with open(os.path.join(FIX, "post_dom.html"),
              encoding="utf-8") as fh:
        html = fh.read()

    def handler(request):
        return httpx.Response(200, text=html)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _run(tmp_path, sender):
    with open(os.path.join(FIX, "sample_config.yaml"),
              encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    data["sources"] = [{"id": "s1", "username": "testchan",
                        "enabled": True, "fetch_mode": "scrape",
                        "proxy": None}]
    cfg_path = str(tmp_path / "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True)
    cfg = load_config(cfg_path)
    store = StateStore(str(tmp_path / "state.json"))
    store.load()
    providers = {"scrape": ScrapeSourceProvider(client=_mock_client())}
    senders = {"bot_api": sender}
    return asyncio.run(
        run_once(cfg, {"BOT_TOKEN": "x"}, store, providers, senders))


def test_mvp_sends_only_new_unpinned(tmp_path):
    sender = FakeSender()
    summary = _run(tmp_path, sender)
    assert summary["sent"] == 1
    assert "vless://" in sender.sent[0][1]


def test_rerun_sends_nothing(tmp_path):
    _run(tmp_path, FakeSender())  # first run publishes post 102
    sender2 = FakeSender()
    summary = _run(tmp_path, sender2)  # same state file -> rerun
    assert summary["sent"] == 0
    assert sender2.sent == []
