"""Integration: testing + location + quarantine routing (T039)."""
import asyncio
import os

import httpx
import yaml

from src.config_loader import load_config
from src.location.geoip import GeoIpLocator
from src.models import Location, TestResult
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
        return SendResult(ok=True, message_id="1")


class FailTester:
    async def test(self, config):
        return TestResult(status="failed", latency_ms=None,
                          checked_at="t", error_class="refused")


class FakeReader:
    def country(self, host):
        raise LookupError(host)


def _run(tmp_path):
    with open(os.path.join(FIX, "sample_config.yaml"),
              encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    data["sources"] = [{"id": "s1", "username": "testchan",
                        "enabled": True, "fetch_mode": "scrape",
                        "proxy": None}]
    data["location"]["enabled"] = True
    data["testing"]["enabled"] = True
    cfg_path = str(tmp_path / "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True)
    cfg = load_config(cfg_path)
    with open(os.path.join(FIX, "post_dom.html"),
              encoding="utf-8") as fh:
        html = fh.read()

    def handler(request):
        return httpx.Response(200, text=html)

    providers = {"scrape": ScrapeSourceProvider(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler)))}
    sender = FakeSender()
    store = StateStore(str(tmp_path / "state.json"))
    store.load()
    locator = GeoIpLocator(reader=FakeReader(),
                           fallback_display="Unknown")
    summary = asyncio.run(run_once(
        cfg, {"BOT_TOKEN": "x"}, store, providers,
        {"bot_api": sender}, tester=FailTester(), locator=locator))
    return summary, sender


def test_failed_goes_to_quarantine_with_location(tmp_path):
    summary, sender = _run(tmp_path)
    ids = [d for d, _ in sender.sent]
    assert ids and all(i == "q" for i in ids)
    assert "Unknown" in sender.sent[0][1]
    assert "ناموفق" in sender.sent[0][1]


def test_testing_disabled_runs_without_labels(tmp_path):
    with open(os.path.join(FIX, "sample_config.yaml"),
              encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    data["sources"] = [{"id": "s1", "username": "testchan",
                        "enabled": True, "fetch_mode": "scrape",
                        "proxy": None}]
    data["testing"]["enabled"] = False
    data["location"]["enabled"] = False
    cfg_path = str(tmp_path / "c2.yaml")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True)
    cfg = load_config(cfg_path)
    with open(os.path.join(FIX, "post_dom.html"),
              encoding="utf-8") as fh:
        html = fh.read()

    def handler2(request):
        return httpx.Response(200, text=html)

    sender = FakeSender()
    store = StateStore(str(tmp_path / "s2.json"))
    store.load()
    providers = {"scrape": ScrapeSourceProvider(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler2)))}
    summary = asyncio.run(run_once(cfg, {"BOT_TOKEN": "x"}, store,
                                   providers, {"bot_api": sender}))
    assert summary["sent"] == 1
    assert "انجام‌نشده" in sender.sent[0][1]
