"""Integration: multi-source isolation + fan-out (T046)."""
import asyncio

import yaml

from src.config_loader import load_config
from src.models import Post
from src.persistence.state_store import StateStore
from src.pipeline import run_once
from src.providers.base import SendResult, SourceFetchError


class FakeSource:
    name = "fake"

    def __init__(self, posts=None, fail=False, fail_ids=()):
        self._posts = posts or []
        self._fail = fail
        self._fail_ids = set(fail_ids)

    async def fetch_new_posts(self, source, since_id):
        if self._fail or source.id in self._fail_ids:
            raise SourceFetchError(source.id, "boom")
        return [p for p in self._posts if p.id > since_id]


class FakeSender:
    name = "fake"

    def __init__(self):
        self.sent = []

    async def send(self, destination, body):
        self.sent.append((destination.id, body))
        return SendResult(ok=True, message_id="1")


def _cfg(tmp_path):
    data = {
        "version": 1,
        "schedule": {"interval_hours": 3},
        "sources": [
            {"id": "s1", "username": "c1", "enabled": True,
             "fetch_mode": "scrape", "proxy": None},
            {"id": "s2", "username": "c2", "enabled": True,
             "fetch_mode": "scrape", "proxy": None},
        ],
        "destinations": [
            {"id": "d1", "chat": "@d1", "enabled": True,
             "sender": "bot_api", "quarantine": False},
            {"id": "d2", "chat": "@d2", "enabled": True,
             "sender": "bot_api", "quarantine": False},
        ],
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
    p = str(tmp_path / "multi.yaml")
    with open(p, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh)
    return load_config(p)


def test_failing_source_does_not_stop_other(tmp_path):
    cfg = _cfg(tmp_path)
    sender = FakeSender()
    providers = {
        # s2 fails while s1 delivers one post in the SAME run
        "scrape": FakeSource([Post(id=1, channel="c1",
                                    text="vless://u@h:443#n")],
                             fail_ids=("s2",)),
    }
    summary = asyncio.run(run_once(cfg, {"BOT_TOKEN": "x"},
                                   _store(tmp_path), providers,
                                   {"bot_api": sender}))
    assert summary["fetched_posts"] == 1
    assert summary["sent"] == 1
    assert summary["errors"] == ["s2: fetch"]


def _store(tmp_path):
    s = StateStore(str(tmp_path / "m.json"))
    s.load()
    return s


def test_round_robin_splits_four_configs(tmp_path):
    cfg = _cfg(tmp_path)
    posts = [Post(id=i, channel="c1",
                  text=f"vless://u{i}@h:443#n") for i in (1, 2, 3, 4)]
    sender = FakeSender()
    summary = asyncio.run(run_once(
        cfg, {"BOT_TOKEN": "x"}, _store(tmp_path),
        {"scrape": FakeSource(posts)}, {"bot_api": sender}))
    assert summary["sent"] == 4
    counts = {}
    for dest_id, _ in sender.sent:
        counts[dest_id] = counts.get(dest_id, 0) + 1
    assert counts == {"d1": 2, "d2": 2}
