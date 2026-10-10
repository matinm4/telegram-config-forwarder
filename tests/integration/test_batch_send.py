"""Batch send: one cycle's configs split round-robin, one batch per dest."""
import asyncio

import yaml

from src.config_loader import load_config
from src.formatting.message import (MAX_LENGTH, build_batch_message,
                                    split_batches)
from src.models import Post
from src.persistence.state_store import StateStore
from src.pipeline import run_once
from src.providers.base import SendResult


class FakeSource:
    name = "fake"

    def __init__(self, posts):
        self._posts = posts

    async def fetch_new_posts(self, source, since_id):
        return [p for p in self._posts if p.id > since_id]


class RecSender:
    name = "rec"

    def __init__(self):
        self.sent = []

    async def send(self, destination, body):
        self.sent.append((destination.id, body))
        return SendResult(ok=True, message_id=str(len(self.sent)))


def _cfg(tmp_path, n_dests=2):
    dests = [
        {"id": f"d{i + 1}", "chat": f"@d{i + 1}", "enabled": True,
         "sender": "bot_api", "quarantine": False}
        for i in range(n_dests)
    ]
    data = {
        "version": 1,
        "schedule": {"interval_hours": 3},
        "sources": [{"id": "s1", "username": "c1", "enabled": True,
                     "fetch_mode": "scrape", "proxy": None}],
        "destinations": dests,
        "distribution": {"strategy": "round_robin", "batch_send": True},
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
    p = str(tmp_path / "batch.yaml")
    with open(p, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh)
    return load_config(p)


def _store(tmp_path):
    s = StateStore(str(tmp_path / "b.json"))
    s.load()
    return s


def _posts(*ids):
    return [Post(id=i, channel="c1",
                 text=f"vless://u{i}@h:443#n{i}") for i in ids]


def test_cycle_configs_split_round_robin_one_batch_each(tmp_path):
    # ۴ کانفیگ تازه در یک چرخه بین ۲ مقصد: هر کانفیگ فقط به یکی می‌رود،
    # سهم هر مقصد در یک پیام دسته‌ای (u1,u3 به یکی و u2,u4 به دیگری).
    cfg = _cfg(tmp_path)
    store = _store(tmp_path)
    sender = RecSender()
    summary = asyncio.run(run_once(
        cfg, {"BOT_TOKEN": "x"}, store,
        {"scrape": FakeSource(_posts(1, 2, 3, 4))},
        {"bot_api": sender}))
    assert summary["sent"] == 4
    assert len(sender.sent) == 2  # دو پیام دسته‌ای، یکی برای هر مقصد
    dests = [d for d, _ in sender.sent]
    assert dests[0] != dests[1]
    bodies = dict(sender.sent)
    d1_body = next(b for d, b in sender.sent if d == dests[0])
    d2_body = next(b for d, b in sender.sent if d == dests[1])
    # هیچ کانفیگی در هر دو پیام نیست (بدون تکرار).
    assert ("vless://u1@h:443#n1" in d1_body) != ("vless://u1@h:443#n1" in d2_body)
    assert "بسته جدید (2 کانفیگ)" in d1_body
    assert "بسته جدید (2 کانفیگ)" in d2_body
    assert len(bodies) == 2


def test_many_configs_one_batch_message(tmp_path):
    cfg = _cfg(tmp_path, n_dests=1)
    store = _store(tmp_path)
    sender = RecSender()
    summary = asyncio.run(run_once(
        cfg, {"BOT_TOKEN": "x"}, store,
        {"scrape": FakeSource(_posts(1, 2, 3))},
        {"bot_api": sender}))
    assert summary["sent"] == 3
    assert len(sender.sent) == 1  # همه در یک پیام دسته‌ای
    _, body = sender.sent[0]
    assert "بسته جدید (3 کانفیگ)" in body
    for i in (1, 2, 3):
        assert f"vless://u{i}@h:443#n{i}" in body


def test_split_batches_respects_length(tmp_path):
    from src.models import Destination
    dest = Destination(id="d", chat="@d", enabled=True, sender="bot_api",
                       quarantine=False)
    raws = [f"vless://u{i}@h:443#n{i}-{'x' * 300}" for i in range(30)]
    batches = split_batches(raws, "Unknown", dest)
    assert len(batches) > 1
    for b in batches:
        assert len(b) <= MAX_LENGTH
    joined = "\n".join(batches)
    for raw in raws:
        assert raw in joined


def test_batch_message_has_footer(tmp_path):
    from src.models import Destination
    dest = Destination(id="d", chat="@d", enabled=True, sender="bot_api",
                       quarantine=False, footer="FOOT")
    body = build_batch_message(["vless://u@h:443#n"], "Unknown", dest)
    assert "FOOT" in body
