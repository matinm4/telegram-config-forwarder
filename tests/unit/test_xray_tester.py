"""Unit tests for the Xray tester with a fake runner (T038)."""
from src.models import ExtractedConfig
from src.testing.xray_tester import XrayTester


def _cfg(raw="vless://u@example.com:443#n"):
    return ExtractedConfig(raw=raw, protocol="vless", source_channel="c",
                           source_post_id=1, exact_hash="h", is_valid=True)


async def _ok(link, timeout_s):
    return ("success", 124, None)


async def _fail(link, timeout_s):
    return ("failed", None, "connection-refused")


async def _slow(link, timeout_s):
    return ("timeout", None, "probe-timeout")


def test_success_with_latency():
    t = XrayTester(xray_path="xray", timeout_s=15, runner=_ok)
    res = __import__("asyncio").run(t.test(_cfg()))
    assert res.status == "success" and res.latency_ms == 124


def test_failed():
    t = XrayTester(xray_path="xray", timeout_s=15, runner=_fail)
    res = __import__("asyncio").run(t.test(_cfg()))
    assert res.status == "failed" and res.latency_ms is None


def test_timeout():
    t = XrayTester(xray_path="xray", timeout_s=15, runner=_slow)
    res = __import__("asyncio").run(t.test(_cfg()))
    assert res.status == "timeout"


def test_missing_binary_skips():
    t = XrayTester(xray_path="/nonexistent/xray", timeout_s=15)
    res = __import__("asyncio").run(t.test(_cfg()))
    assert res.status == "skipped"


async def _noop_sleep(_):
    return None


def test_timeout_retries_then_succeeds():
    calls = []

    async def flaky(link, timeout_s):
        calls.append(1)
        if len(calls) < 2:
            return ("timeout", None, "probe-timeout")
        return ("success", 50, None)

    t = XrayTester(xray_path="xray", timeout_s=15, runner=flaky,
                   max_attempts=3, backoff_s=(0,), sleep=_noop_sleep)
    res = __import__("asyncio").run(t.test(_cfg()))
    assert res.status == "success" and res.latency_ms == 50
    assert len(calls) == 2


def test_refused_is_not_retried():
    calls = []

    async def refused(link, timeout_s):
        calls.append(1)
        return ("failed", None, "connection-refused")

    t = XrayTester(xray_path="xray", timeout_s=15, runner=refused,
                   max_attempts=3, backoff_s=(0,), sleep=_noop_sleep)
    res = __import__("asyncio").run(t.test(_cfg()))
    assert res.status == "failed" and len(calls) == 1


def test_unsupported_protocol_skips():
    # سیاست T066: پروتکل غیرقابل تست، failed نیست بلکه skipped است.
    t = XrayTester(xray_path="xray", timeout_s=15, runner=_ok)
    cfg = _cfg(raw="hysteria2://pw@h:443")
    cfg.protocol = "hysteria2"
    res = __import__("asyncio").run(t.test(cfg))
    assert res.status == "skipped"
    assert res.error_class == "unsupported-protocol"
