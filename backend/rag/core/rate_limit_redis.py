"""Fixed-window rate limit using Redis INCR (no Lua; works with fakeredis + production Redis)."""

from __future__ import annotations

import time
from typing import Any


def fixed_window_allow(
    client: Any,
    key: str,
    limit: int,
    window_sec: int = 60,
) -> bool:
    """Return True if request is allowed; False if rate limited.

    Counts requests per ``key`` per time bucket of ``window_sec`` seconds.
    ``client`` must support ``.incr()`` and ``.expire()`` like ``redis.Redis`` or fakeredis.
    """
    if limit <= 0:
        return True

    bucket = int(time.time() // window_sec)
    window_key = f"{key}:w:{bucket}"
    n = int(client.incr(window_key))
    if n == 1:
        client.expire(window_key, window_sec + 10)
    return n <= limit
