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

BATCH_HEADER = "📦 بسته جدید ({count} کانفیگ)\n"


def render_batch_message(configs: list[str], location_display: str,
                           destination: Destination) -> str:
    """Render full batch body WITHOUT truncation (for size measuring)."""
    blocks = "\n\n".join(f"<code>{raw}</code>" for raw in configs)
    footer = ""
    if destination.footer:
        footer = f"\n\n{destination.footer}"
    elif destination.append_username:
        footer = f"\n📢 {destination.chat}"
    return (f"{BATCH_HEADER.format(count=len(configs))}"
            f"📍 موقعیت: {location_display}\n\n"
            f"{blocks}{footer}")


def build_batch_message(configs: list[str], location_display: str,
                        destination: Destination) -> str:
    """Render one batch message holding many configs (batch send mode)."""
    body = render_batch_message(configs, location_display, destination)
    if len(body) > MAX_LENGTH:
        # قرارداد: کانفیگ بدون تغییر می‌ماند، سقف فقط با بریدن بسته رعایت می‌شود.
        body = body[:MAX_LENGTH]
    return body


def split_batches(configs: list[str], location_display: str,
                  destination: Destination) -> list[str]:
    """Split configs into batch messages that each fit MAX_LENGTH."""
    batches: list[str] = []
    current: list[str] = []
    for raw in configs:
        candidate = current + [raw]
        if len(render_batch_message(candidate, location_display,
                                    destination)) > MAX_LENGTH:
            if not current:
                # یک کانفیگ تنها هم جا نشد؛ به‌تنهایی بفرست (بریده‌شده).
                batches.append(build_batch_message([raw], location_display,
                                                   destination))
            else:
                batches.append(build_batch_message(current, location_display,
                                                   destination))
                current = [raw]
        else:
            current = candidate
    if current:
        batches.append(build_batch_message(current, location_display,
                                           destination))
    return batches

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
    if destination.footer:
        username_block = f"\n\n{destination.footer}"
    elif destination.append_username:
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
