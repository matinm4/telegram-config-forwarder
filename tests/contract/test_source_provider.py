"""Contract tests for SourceProvider implementations (T016)."""
import pytest

from src.models import Post, SourceChannel
from src.providers.base import SourceProvider


class FakeProvider:
    name = "fake"

    def __init__(self, posts):
        self._posts = sorted(posts, key=lambda p: p.id)

    async def fetch_new_posts(self, source, since_id):
        return [p for p in self._posts
                if p.id > since_id and not p.is_pinned]


def _src():
    return SourceChannel(id="s1", username="testchan", enabled=True,
                         fetch_mode="scrape", proxy=None)


def _posts():
    return [Post(id=100, channel="testchan", text="a"),
            Post(id=101, channel="testchan", text="b", is_pinned=True),
            Post(id=102, channel="testchan", text="c")]


def test_conforms_to_protocol():
    assert isinstance(FakeProvider(_posts()), SourceProvider)


async def test_only_new_unpinned_ascending():
    prov = FakeProvider(_posts())
    got = await prov.fetch_new_posts(_src(), 100)
    assert [p.id for p in got] == [102]


async def test_empty_when_nothing_new():
    prov = FakeProvider(_posts())
    assert await prov.fetch_new_posts(_src(), 102) == []
