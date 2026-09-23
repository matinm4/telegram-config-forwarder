"""Pipeline orchestration across the 13 stages (T029-T050).

Story hooks (cleaner, locator, tester, distributor, telethon) are optional
so the MVP runs with safe defaults; later stories plug in real
implementations without changing this flow.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Union

from src.config_loader import AppConfig, Secrets
from src.distribution.distributor import Distributor
from src.extraction.link_finder import find_links
from src.extraction.normalizer import build_record
from src.filtering.cleaner import Cleaner
from src.formatting.message import build_message
from src.models import Location, RunRecord, TestResult
from src.persistence.state_store import StateStore
from src.providers.base import (SendResult, SourceAccessError,
                                SourceFetchError, run_with_retry)
from src.providers.bot_sender import BotApiSender
from src.providers.scrape_source import ScrapeSourceProvider

log = logging.getLogger("forwarder")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_once(config: AppConfig,
                   secrets: Union[Secrets, Mapping[str, str]],
                   store: StateStore,
                   providers: Optional[dict] = None,
                   senders: Optional[dict] = None,
                   tester: Any = None,
                   locator: Any = None,
                   cleaner: Any = None,
                   distributor: Optional[Distributor] = None) -> dict:
    """Execute one full cycle; never let one item stop the rest (FR-024)."""
    token = (secrets.bot_token if isinstance(secrets, Secrets)
             else secrets.get("BOT_TOKEN", ""))
    providers = providers or {"scrape": ScrapeSourceProvider()}
    senders = senders or {"bot_api": BotApiSender(token)}
    distributor = distributor or Distributor(
        strategy=config.distribution.strategy,
        cursor=store.state.distribution_cursor,
        counters=store.state.distribution_counters)
    if cleaner is None and config.filtering.enabled:
        cleaner = Cleaner(config.filtering.rules)
    store.load()
    summary = {"fetched_posts": 0, "extracted": 0, "sent": 0,
               "failed": 0, "skipped_duplicates": 0, "errors": []}
    started = _utcnow()

    destinations = [d for d in config.destinations if d.enabled]
    targets = [d for d in destinations if not d.quarantine]
    quarantine_targets = [d for d in destinations if d.quarantine]

    sem = asyncio.Semaphore(config.concurrency.source_limit)

    async def _guarded(source):
        async with sem:
            return await _run_source(config, source, store, providers,
                                     senders, targets, quarantine_targets,
                                     tester, locator, cleaner, distributor,
                                     summary)

    await asyncio.gather(*(_guarded(s) for s in config.sources
                           if s.enabled))
    store.state.distribution_cursor = distributor.cursor
    store.state.distribution_counters = dict(distributor._counters)
    store.append_run(RunRecord(
        started_at=started, finished_at=_utcnow(),
        fetched_posts=summary["fetched_posts"],
        extracted=summary["extracted"], sent=summary["sent"],
        failed=summary["failed"], errors=summary["errors"][:10]))
    store.save()
    return summary


def _provider_order(source, fails: int, config: AppConfig,
                    providers: dict) -> list:
    primary = {"scrape": "scrape", "telethon": "telethon"}.get(
        source.fetch_mode, "scrape")
    secondary = "telethon" if primary == "scrape" else "scrape"
    order = [primary]
    if (source.fetch_mode == "auto"
            and config.fallback.source_fallback_enabled
            and secondary in providers):
        if fails >= config.fallback.after_failures:
            order = [secondary, primary]
        else:
            order = [primary, secondary]
    return [providers[name] for name in order if name in providers]


async def _run_source(config: AppConfig, source, store: StateStore,
                      providers, senders, targets, quarantine_targets,
                      tester, locator, cleaner, distributor,
                      summary: dict) -> None:
    key = f"source:{source.id}"
    fails = store.state.consecutive_failures.get(key, 0)
    since_id = store.get_last_id(source.id)
    posts: list = []
    last_error: Optional[str] = None
    for provider in _provider_order(source, fails, config, providers):
        try:
            posts = await provider.fetch_new_posts(source, since_id)
            store.state.consecutive_failures[key] = 0
            last_error = None
            break
        except SourceAccessError:
            last_error = "access"
            break
        except SourceFetchError:
            last_error = "fetch"
            continue
    if last_error:
        log.warning("منبع %s رد شد (%s).", source.id, last_error)
        summary["errors"].append(f"{source.id}: {last_error}")
        fails = store.state.consecutive_failures.get(key, 0) + 1
        store.state.consecutive_failures[key] = fails
        return
    summary["fetched_posts"] += len(posts)
    max_seen = since_id
    for post in posts:
        max_seen = max(max_seen, post.id)
        try:
            await _process_post(config, post, source.id, targets,
                                quarantine_targets, store, senders,
                                tester, locator, cleaner, distributor,
                                summary)
        except Exception:  # noqa: BLE001 - isolate per-item failures
            log.warning("پردازش پست %s ناموفق بود؛ ادامه.", post.id)
            summary["failed"] += 1
    store.set_last_id(source.id, max_seen)


async def _process_post(config: AppConfig, post, source_id: str,
                        targets, quarantine_targets, store: StateStore,
                        senders, tester, locator, cleaner,
                        distributor: Distributor, summary: dict) -> None:
    text = post.text or ""
    if cleaner is not None:
        text = cleaner.clean(text, scope="text")
    for raw in find_links(text):
        record = build_record(raw, source_id, post.id)
        if not record.is_valid:
            summary["failed"] += 1
            continue
        summary["extracted"] += 1
        if store.is_published(record.exact_hash):
            summary["skipped_duplicates"] += 1
            continue
        location = (locator.locate(record) if locator
                    else Location(
                        display=config.location.fallback_display))
        result = (await tester.test(record) if tester
                  else TestResult(status="skipped"))
        if result.status in ("failed", "timeout"):
            item_targets = quarantine_targets
            if not item_targets:
                log.warning("قرنطینه تعریف نشده؛ کانفیگ حذف شد.")
                summary["failed"] += 1
                store.mark_published(record.exact_hash)
                continue
        else:
            item_targets = distributor.select(targets, source_id)
        for destination in item_targets:
            body = build_message(record, location, result, destination)
            if destination.rules:
                body = Cleaner(destination.rules).clean(body, scope="text")
            send_res = await _send_with_fallback(config, destination,
                                                 body, senders, store)
            if send_res.ok:
                summary["sent"] += 1
            else:
                summary["failed"] += 1
        store.mark_published(record.exact_hash)


def _sender_order(destination, fails: int, config: AppConfig,
                  senders: dict) -> list:
    """Primary first; fallback after `after_failures` (FR-025, T054)."""
    mode = destination.sender
    if mode != "auto":
        return [senders[mode]] if mode in senders else []
    order = ["bot_api", "telethon"]
    if (config.fallback.sender_fallback_enabled
            and fails >= config.fallback.after_failures):
        order = ["telethon", "bot_api"]
    return [senders[name] for name in order if name in senders]


async def _send_with_fallback(config: AppConfig, destination, body: str,
                              senders: dict,
                              store: StateStore) -> SendResult:
    key = f"sender:{destination.id}"
    fails = store.state.consecutive_failures.get(key, 0)
    last = SendResult(ok=False, error_class="permanent")
    for sender in _sender_order(destination, fails, config, senders):
        last = await run_with_retry(
            lambda: sender.send(destination, body),
            max_attempts=config.retry.max_attempts,
            backoff_s=tuple(config.retry.backoff_s))
        if last.ok:
            store.state.consecutive_failures[key] = 0
            return last
        if last.error_class != "retryable":
            continue  # permanent on this sender: try the next one
    fails = store.state.consecutive_failures.get(key, 0) + 1
    store.state.consecutive_failures[key] = fails
    log.warning("ارسال به %s ناموفق بود.", destination.id)
    return last
