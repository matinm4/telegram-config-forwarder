"""Connectivity testing through Xray (T041).

Measures application-level latency only (TCP + HTTP via the local Xray
proxy) - never ICMP. The actual singe run is injectable so unit tests never
need the real binary; a missing binary degrades to `skipped`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import socket
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlsplit

import httpx

from src.models import ExtractedConfig, TestResult

log = logging.getLogger("forwarder")
PROBE_URL = "http://www.gstatic.com/generate_204"
SUPPORTED = {"vless", "vmess", "trojan", "ss"}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_outbound(raw: str, protocol: str) -> Optional[dict]:
    """Translate a config link into an Xray outbound fragment."""
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if not parts.hostname or not parts.port:
        return None
    address, port = parts.hostname, parts.port
    if protocol == "vless":
        return {"protocol": "vless",
                "settings": {"vnext": [{"address": address, "port": port,
                                        "users": [{"id": parts.username or "",
                                                   "flow": ""}]}]}}
    if protocol == "vmess":
        return {"protocol": "vmess",
                "settings": {"vnext": [{"address": address, "port": port,
                                        "users": [{"id": parts.username or "",
                                                   "alterId": 0}]}]}}
    if protocol == "trojan":
        return {"protocol": "trojan",
                "settings": {"servers": [{"address": address, "port": port,
                                          "password": parts.username or ""}]}}
    if protocol == "ss":
        return {"protocol": "shadowsocks",
                "settings": {"servers": [{"address": address, "port": port,
                                          "method": "aes-256-gcm",
                                          "password": parts.username or ""}]}}
    return None


async def _default_runner(link: str, timeout_s: int):
    """Real run: start xray (path from env), probe, stop. Returns tuple."""
    from src.extraction.protocol_parser import parse_link
    proto = parse_link(link, "", 0).protocol
    outbound = build_outbound(link, proto)
    if outbound is None:
        return ("failed", None, "unsupported")
    xray = shutil.which("xray") or os.environ.get("XRAY_PATH", "xray")
    port = _free_port()
    conf = {"inbounds": [{"port": port, "protocol": "socks",
                          "settings": {"udp": False}}],
            "outbounds": [outbound]}
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as fh:
        json.dump(conf, fh)
        conf_path = fh.name
    proc = await asyncio.create_subprocess_exec(
        xray, "run", "-c", conf_path,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL)
    try:
        await asyncio.sleep(1.0)
        if proc.returncode is not None:
            return ("failed", None, "xray-exit")
        proxy = f"socks5h://127.0.0.1:{port}"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(proxy=proxy,
                                         timeout=timeout_s) as client:
                resp = await client.get(PROBE_URL)
        except (httpx.TimeoutException, asyncio.TimeoutError):
            return ("timeout", None, "probe-timeout")
        except httpx.HTTPError:
            return ("failed", None, "probe-error")
        elapsed_ms = int((time.monotonic() - start) * 1000)
        if resp.status_code in (200, 204):
            return ("success", elapsed_ms, None)
        return ("failed", None, f"http-{resp.status_code}")
    finally:
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5)
        except Exception:  # noqa: BLE001 - best-effort cleanup
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        try:
            os.unlink(conf_path)
        except OSError:
            pass


Runner = Callable[[str, int], Awaitable[tuple]]


class XrayTester:
    """Global (once-per-config) tester with concurrency limit."""

    def __init__(self, xray_path: str = "xray", timeout_s: int = 15,
                 max_concurrency: int = 4,
                 runner: Optional[Runner] = None,
                 max_attempts: int = 3,
                 backoff_s: tuple = (1, 2, 4),
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
                 ) -> None:
        self._xray_path = xray_path
        self._timeout = timeout_s
        self._sem = asyncio.Semaphore(max_concurrency)
        self._runner = runner
        self._max_attempts = max(1, max_attempts)
        self._backoff = tuple(backoff_s) or (1,)
        self._sleep = sleep

    def _available(self) -> bool:
        return self._runner is not None or (
            shutil.which(self._xray_path) is not None
            or os.path.exists(self._xray_path))

    async def test(self, config: ExtractedConfig) -> TestResult:
        now = datetime.now(timezone.utc).isoformat()
        if config.protocol not in SUPPORTED:
            # سیاست مصوب T066: ناتوانی آزمون‌گر دلیلی بر خرابی کانفیگ
            # نیست؛ رد می‌شود تا مسیر عادی (نه قرنطینه) برود.
            log.warning("پروتکل %s قابل تست نیست؛ رد شد.",
                        config.protocol)
            return TestResult(status="skipped", checked_at=now,
                              error_class="unsupported-protocol")
        if not self._available():
            log.warning("باینری Xray یافت نشد؛ تست رد شد.")
            return TestResult(status="skipped", checked_at=now)
        runner = self._runner or _default_runner
        async with self._sem:
            for attempt in range(self._max_attempts):
                try:
                    status, latency, err = await runner(config.raw,
                                                        self._timeout)
                except Exception:  # noqa: BLE001 - isolate tester crashes
                    status, latency, err = ("failed", None, "runner-error")
                if status not in ("success", "failed", "timeout"):
                    status = "failed"
                retryable = (status == "timeout"
                             or err == "runner-error")
                if not retryable or attempt >= self._max_attempts - 1:
                    return TestResult(status=status, latency_ms=latency,
                                      checked_at=now, error_class=err)
                await self._sleep(self._backoff[min(
                    attempt, len(self._backoff) - 1)])
        return TestResult(status="failed", checked_at=now,
                          error_class="runner-error")
