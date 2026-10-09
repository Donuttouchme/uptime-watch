import httpx2

from uptime_watch.checks import USER_AGENT, check_url, make_client

URL = "https://example.com/"


def client_answering(handler):
    return make_client(10, transport=httpx2.MockTransport(handler))


def test_2xx_is_up_with_status_and_time():
    outcome = check_url(client_answering(lambda request: httpx2.Response(200)), URL)

    assert outcome.up is True
    assert outcome.status_code == 200
    assert outcome.response_time_ms is not None and outcome.response_time_ms >= 0
    assert outcome.error is None


def test_3xx_is_up_and_the_redirect_is_not_followed():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx2.Response(301, headers={"Location": "https://example.com/elsewhere"})

    outcome = check_url(client_answering(handler), URL)

    assert outcome.up is True
    assert outcome.status_code == 301
    assert calls == [URL]


def test_4xx_and_5xx_are_down_with_status():
    for status in (404, 500, 503):
        outcome = check_url(client_answering(lambda request, s=status: httpx2.Response(s)), URL)

        assert outcome.up is False
        assert outcome.status_code == status
        assert outcome.error is None


def test_timeout_is_down_without_status():
    def handler(request):
        raise httpx2.ReadTimeout("timed out", request=request)

    outcome = check_url(client_answering(handler), URL)

    assert (outcome.up, outcome.status_code, outcome.response_time_ms) == (False, None, None)
    assert outcome.error == "timeout"


def test_headers_arriving_after_the_total_timeout_are_a_timeout(monkeypatch):
    # httpx2 times each phase separately; the check as a whole must still fit the timeout.
    readings = [1000.0]  # the check's start; every later reading is 11 s on
    monkeypatch.setattr(
        "uptime_watch.checks.time.perf_counter", lambda: readings.pop() if readings else 1011.0
    )

    outcome = check_url(client_answering(lambda request: httpx2.Response(200)), URL)

    assert (outcome.up, outcome.status_code, outcome.response_time_ms) == (False, None, None)
    assert outcome.error == "timeout"


def test_dns_failure_is_named():
    def handler(request):
        raise httpx2.ConnectError("[Errno -2] Name or service not known", request=request)

    assert check_url(client_answering(handler), URL).error == "DNS lookup failed"


def test_refused_connection_is_named():
    def handler(request):
        raise httpx2.ConnectError("[Errno 111] Connection refused", request=request)

    assert check_url(client_answering(handler), URL).error == "connection refused"


def test_tls_failure_is_named():
    def handler(request):
        raise httpx2.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed", request=request)

    assert check_url(client_answering(handler), URL).error == "TLS error"


def test_other_transport_errors_are_down_with_a_reason():
    def handler(request):
        raise httpx2.RemoteProtocolError("Server disconnected", request=request)

    outcome = check_url(client_answering(handler), URL)

    assert outcome.up is False
    assert outcome.error == "request failed: RemoteProtocolError"


def test_status_outside_100_to_599_is_down_without_status():
    outcome = check_url(client_answering(lambda request: httpx2.Response(999)), URL)

    assert outcome.up is False
    assert outcome.status_code is None
    assert outcome.error == "invalid status code 999"


def test_the_body_is_never_read():
    def endless_body():
        raise AssertionError("the check must not read the body")
        yield b""  # makes this a generator

    outcome = check_url(
        client_answering(lambda request: httpx2.Response(200, content=endless_body())), URL
    )

    assert outcome.up is True


def test_check_sends_the_user_agent():
    seen = []

    def handler(request):
        seen.append(request.headers["user-agent"])
        return httpx2.Response(200)

    check_url(client_answering(handler), URL)

    assert seen == [USER_AGENT]


def test_client_uses_the_timeout_and_does_not_follow_redirects():
    client = make_client(7)

    assert client.timeout.read == 7
    assert client.follow_redirects is False
