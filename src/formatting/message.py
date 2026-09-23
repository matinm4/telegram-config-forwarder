"""Message formatting with per-destination templates (T028)."""
from __future__ import annotations

from typing import Optional

from src.models import Destination, ExtractedConfig, Location, TestResult

STATUS_FA = {
    "success": "موفق",
    "failed": "ناموفق",
    "timeout": "تمام‌شدن زمان",
    "skipped": "انجام‌نشده",
}

DEFAULT_TEMPLATE = (
    "🔗 کانفیگ جدید ({protocol}) — {location}\n"
    "\n"
    "<code>{config}</code>\n"
    "\n"
    "📍 موقعیت: {location}\n"
    "🧪 تست: {test}{latency}"
    "{username_block}"
)

TEMPLATES = {"default": DEFAULT_TEMPLATE}
MAX_LENGTH = 4096


def get_template(name: str) -> str:
    """Return a named template, falling back to default (T035)."""
    return TEMPLATES.get(name or "default", DEFAULT_TEMPLATE)


def build_message(config: ExtractedConfig, location: Location,
                  result: TestResult, destination: Destination,
                  template: Optional[str] = None) -> str:
    """Render the final message body (never includes secrets)."""
    latency = (f" ({result.latency_ms} میلی‌ثانیه)"
               if result.latency_ms is not None else "")
    username_block = ""
    if destination.append_username:
        username_block = f"\n📢 {destination.chat}"
    body = (template or get_template(destination.message_template)).format(
        protocol=config.protocol,
        location=location.display,
        config=config.raw,
        test=STATUS_FA.get(result.status, result.status),
        latency=latency,
        username_block=username_block,
    )
    if len(body) > MAX_LENGTH:
        # قرارداد: کانفیگ بدون تغییر می‌ماند، فراداده خلاصه می‌شود.
        body = f"🔗 کانفیگ جدید ({config.protocol})\n\n<code>{config.raw}</code>"
        body = body[:MAX_LENGTH]
    return body
