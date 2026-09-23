"""Unit tests for the shared retry policy FR-033 (T052)."""
from src.providers.base import SendResult, run_with_retry


async def _noop_sleep(_):
    return None


def _run(coro):
    return __import__("asyncio").run(coro)


def test_succeeds_after_retries():
    calls = []

    async def op():
        calls.append(1)
        if len(calls) < 3:
            return SendResult(ok=False, error_class="retryable")
        return SendResult(ok=True, message_id="1")

    res = _run(run_with_retry(op, sleep=_noop_sleep))
    assert res.ok and len(calls) == 3


def test_gives_up_after_max_attempts():
    async def op():
        return SendResult(ok=False, error_class="retryable")

    res = _run(run_with_retry(op, max_attempts=3, sleep=_noop_sleep))
    assert res.ok is False


def test_permanent_does_not_retry():
    calls = []

    async def op():
        calls.append(1)
        return SendResult(ok=False, error_class="permanent")

    res = _run(run_with_retry(op, sleep=_noop_sleep))
    assert res.ok is False and len(calls) == 1


def test_backoff_schedule():
    waits = []

    async def sleep(s):
        waits.append(s)

    async def op():
        return SendResult(ok=False, error_class="retryable")

    _run(run_with_retry(op, backoff_s=(1, 2, 4), sleep=sleep))
    assert waits == [1, 2]
