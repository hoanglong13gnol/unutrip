"""Redis fixed-window limiter (fakeredis; no daemon)."""

import fakeredis

from core.rate_limit_redis import fixed_window_allow


def test_fixed_window_blocks_after_limit() -> None:
    r = fakeredis.FakeRedis(decode_responses=True)
    key = "test:rl:client1"
    limit = 5
    for _ in range(limit):
        assert fixed_window_allow(r, key, limit, 60) is True
    assert fixed_window_allow(r, key, limit, 60) is False


def test_fixed_window_zero_limit_means_unlimited() -> None:
    r = fakeredis.FakeRedis(decode_responses=True)
    assert fixed_window_allow(r, "k", 0, 60) is True
