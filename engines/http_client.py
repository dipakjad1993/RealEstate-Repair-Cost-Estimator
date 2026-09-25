"""Shared HTTP session: retries, backoff, timeouts, latency metrics (enterprise).

All live gov fetchers must use shared_session() — never bare requests.get.
Latency per host is recorded in-memory for the Health page.
"""

import logging
import time
from collections import defaultdict, deque

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_LAT = defaultdict(lambda: deque(maxlen=50))

_session = None


def shared_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "RepairEstimator/3.1 (enterprise; contact: support@example.com)",
            "Accept": "application/json",
        }
    )
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    _session = s
    return _session


def timed_get(url, params=None, timeout=15):
    s = shared_session()
    t0 = time.perf_counter()
    try:
        r = s.get(url, params=params, timeout=timeout)
        dt = (time.perf_counter() - t0) * 1000
        _record(url, dt, r.status_code)
        return r
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        _record(url, dt, "ERR")
        raise e


def timed_post(url, json_body=None, timeout=20):
    s = shared_session()
    t0 = time.perf_counter()
    try:
        r = s.post(url, json=json_body, timeout=timeout)
        dt = (time.perf_counter() - t0) * 1000
        _record(url, dt, r.status_code)
        return r
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        _record(url, dt, "ERR")
        raise e


def _record(url, ms, status):
    try:
        from urllib.parse import urlparse

        host = urlparse(url).netloc or url[:40]
    except Exception:
        host = "unknown"
    _LAT[host].append({"ms": round(ms, 1), "status": status, "at": time.time()})


def latency_summary():
    out = {}
    for host, samples in _LAT.items():
        ms = [x["ms"] for x in samples if isinstance(x["ms"], int | float)]
        if not ms:
            continue
        out[host] = {
            "calls": len(ms),
            "p50_ms": round(sorted(ms)[len(ms) // 2], 1),
            "max_ms": round(max(ms), 1),
            "last_status": samples[-1]["status"],
        }
    return out
