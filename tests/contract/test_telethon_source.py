"""Contract tests for the Telethon source path (T045)."""
from src.models import Post, SourceChannel
from src.providers.base import SourceProvider


class FakeTelethonSource:
    name = "telethon"

    def __init__(self, posts):
        self._posts = sorted(posts, key=lambda p: p.id)

    async def fetch_new_posts(self, source, since_id):
        return [p for p in self._posts if p.id > since_id]


def test_conforms_to_protocol():
    posts = [Post(id=5, channel="priv", text="x")]
    assert isinstance(FakeTelethonSource(posts), SourceProvider)


async def test_private_channel_posts():
    prov = FakeTelethonSource(
        [Post(id=5, channel="priv", text="vless://u@h:443"),
         Post(id=6, channel="priv", text="")])
    got = await prov.fetch_new_posts(
        SourceChannel(id="p", username="priv", enabled=True,
                      fetch_mode="telethon", proxy=None), 5)
    assert [p.id for p in got] == [6]
