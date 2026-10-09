"""One Check of one URL (CONTEXT.md: Check, Up). No database, no queue."""

import time
from dataclasses import dataclass

import httpx2

USER_AGENT = "uptime-watch/0.1"

_DNS_FAILURES = (
    "name or service not known",
    "temporary failure in name resolution",
    "nodename nor servname",
    "no address associated",
)


@dataclass(frozen=True)
class CheckOutcome:
    up: bool
    status_code: int | None
    response_time_ms: int | None
    error: str | None


def make_client(
    timeout_seconds: float, transport: httpx2.BaseTransport | None = None
) -> httpx2.Client:
    # 3xx counts as up, so redirects are not followed: we check the URL that was registered.
    return httpx2.Client(
        timeout=timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": USER_AGENT},
        transport=transport,
    )


def check_url(client: httpx2.Client, url: str) -> CheckOutcome:
    start = time.perf_counter()
    try:
        # stream() returns once the headers are in; leaving the block closes the
        # connection without reading the body, so the response time ends at the headers.
        with client.stream("GET", url) as response:
            elapsed = time.perf_counter() - start
            status = response.status_code
    except httpx2.TimeoutException:
        return _down("timeout")
    except httpx2.HTTPError as exc:
        return _down(_describe(exc))

    # httpx2 limits each phase on its own, so the total is checked here. make_client
    # sets one value for every phase, so read is the configured timeout.
    timeout = client.timeout.read
    if timeout is not None and elapsed > timeout:
        return _down("timeout")
    elapsed_ms = round(elapsed * 1000)

    if not 100 <= status <= 599:
        return _down(f"invalid status code {status}")
    return CheckOutcome(
        up=200 <= status < 400, status_code=status, response_time_ms=elapsed_ms, error=None
    )


def _down(error: str) -> CheckOutcome:
    return CheckOutcome(up=False, status_code=None, response_time_ms=None, error=error[:200])


def _describe(exc: httpx2.HTTPError) -> str:
    if isinstance(exc, httpx2.ConnectError):
        message = str(exc).lower()
        if any(text in message for text in _DNS_FAILURES):
            return "DNS lookup failed"
        if "connection refused" in message:
            return "connection refused"
        if "certificate" in message or "ssl" in message or "tls" in message:
            return "TLS error"
        return "connection failed"
    return f"request failed: {type(exc).__name__}"
