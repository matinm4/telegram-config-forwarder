"""Unit tests for distribution strategies (T044)."""
from src.distribution.distributor import Distributor
from src.models import Destination


def _dests():
    return [Destination(id="a", chat="@a", enabled=True, sender="bot_api",
                        quarantine=False),
            Destination(id="b", chat="@b", enabled=True, sender="bot_api",
                        quarantine=False)]


def test_round_robin_rotates():
    dist = Distributor(strategy="round_robin", cursor=0)
    first = dist.select(_dests(), "s1")
    second = dist.select(_dests(), "s1")
    assert [d.id for d in first] == ["a"]
    assert [d.id for d in second] == ["b"]
    assert dist.cursor == 2


def test_broadcast_returns_all():
    dist = Distributor(strategy="broadcast")
    assert len(dist.select(_dests(), "s1")) == 2


def test_source_based_is_stable():
    dist = Distributor(strategy="source_based")
    assert (dist.select(_dests(), "s1")[0].id
            == dist.select(_dests(), "s1")[0].id)


def test_quarantine_never_selected():
    dests = _dests() + [Destination(id="q", chat="@q", enabled=True,
                                    sender="bot_api", quarantine=True)]
    dist = Distributor(strategy="broadcast")
    assert all(not d.quarantine for d in dist.select(dests, "s1"))


def test_unknown_strategy_falls_back_to_round_robin():
    dist = Distributor(strategy="weird")
    assert len(dist.select(_dests(), "s1")) == 1


def test_balanced_counters_survive_across_instances():
    # رفتار T070: شمارنده‌ها از وضعیت بازیابی می‌شوند.
    first = Distributor(strategy="balanced", counters={"a": 0, "b": 0})
    assert [d.id for d in first.select(_dests(), "s")] == ["a"]
    second = Distributor(strategy="balanced",
                         counters=dict(first._counters))
    assert [d.id for d in second.select(_dests(), "s")] == ["b"]
