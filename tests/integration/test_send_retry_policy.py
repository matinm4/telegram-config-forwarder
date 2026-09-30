"""Failed sends must not burn the config hash (repost retry policy)."""
import asyncio

import yaml

from src.config_loader import load_config
from src.models import Post
from src.persistence.state_store import StateStore
from src.pipeline import run_once
from src.providers.base import SendResult


class FailSender:
    name = "fail"

    async def send(self, destination, body):
        return SendResult(ok=False, error_class="permanent")


class OkSender:
    name = "ok"

    def __init__(self):
        self.sent = []

    async def send(self, destination, body):
        self.sent.append((destination.id, body))
        return SendResult(ok=True, message_id="1")


class FakeSource:
    name = "fake"

    def __init__(self, posts):
        self._posts = posts

    async def fetch_new_posts(self, source, since_id):
        return [p for p in self._posts if p.id > since_id]


def _cfg(tmp_path):
    data = {
        "version": 1,
        "schedule": {"interval_hours": 3},
        "sources": [{"id": "s1", "username": "c1", "enabled": True,
                     "fetch_mode": "scrape", "proxy": None}],
        "destinations": [{"id": "d1", "chat": "@d1", "enabled": True,
                          "sender": "bot_api", "quarantine": False}],
        "distribution": {"strategy": "round_robin"},
        "filtering": {"enabled": False, "rules": [],
                      "append_destination_username": False},
        "location": {"enabled": False, "fallback_display": "Unknown"},
        "testing": {"enabled": False, "timeout_s": 15,
                    "xray_version": "v1"},
        "fallback": {"source_fallback_enabled": True,
                     "sender_fallback_enabled": True,
                     "after_failures": 2},
        "logging": {"level": "INFO"},
    }
    p = str(tmp_path / "retry.yaml")
    with open(p, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh)
    return load_config(p)


def _store(tmp_path):
    s = StateStore(str(tmp_path / "retry.json"))
    s.load()
    return s


def test_failed_send_keeps_hash_for_repost_retry(tmp_path):
    cfg = _cfg(tmp_path)
    store = _store(tmp_path)
    # همان کانفیگ با شناسه پست جدید (رفتار کانال‌های تکرارشونده)
    posts = [Post(id=1, channel="c1", text="vless://u@h:443#n"),
             Post(id=2, channel="c1", text="vless://u@h:443#n"),
             Post(id=3, channel="c1", text="vless://u@h:443#n")]
    summary = asyncio.run(run_once(
        cfg, {"BOT_TOKEN": "x"}, store,
        {"scrape": FakeSource(posts[:1])}, {"bot_api": FailSender()}))
    assert summary["sent"] == 0
    assert store.state.published_hashes == []  # hash not burned

    sender = OkSender()
    # repost همان کانفیگ با شناسه جدید (پست‌های تکرارشونده منبع)
    summary = asyncio.run(run_once(
        cfg, {"BOT_TOKEN": "x"}, store, {"scrape": FakeSource(posts)},
        {"bot_api": sender}))
    assert summary["sent"] == 1  # repost retried and delivered
    assert len(store.state.published_hashes) == 1


def test_successful_send_marks_hash(tmp_path):
    cfg = _cfg(tmp_path)
    store = _store(tmp_path)
    posts = [Post(id=1, channel="c1", text="vless://u@h:443#n")]
    sender = OkSender()
    asyncio.run(run_once(cfg, {"BOT_TOKEN": "x"}, store,
                         {"scrape": FakeSource(posts)},
                         {"bot_api": sender}))
    # همان پست با همان شناسه دیگر دیده نمی‌شود و چیزی ارسال نمی‌شود
    summary = asyncio.run(run_once(cfg, {"BOT_TOKEN": "x"}, store,
                                   {"scrape": FakeSource(posts)},
                                   {"bot_api": sender}))
    assert summary["sent"] == 0
    assert len(sender.sent) == 1
