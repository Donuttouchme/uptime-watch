from datetime import UTC, datetime

import httpx2
from sqlalchemy import func, select, text

from uptime_watch.checks import make_client
from uptime_watch.models import Monitor, Result
from uptime_watch.worker import check_and_record


def client_answering(handler):
    return make_client(10, transport=httpx2.MockTransport(handler))


def ok(request):
    return httpx2.Response(200)


def add_monitor(session, **fields):
    monitor = Monitor(name="Example", url="https://example.com/", **fields)
    session.add(monitor)
    session.commit()
    return monitor


def count_results(session):
    return session.scalar(select(func.count()).select_from(Result))


def test_records_an_up_result(session):
    monitor = add_monitor(session)
    before = datetime.now(UTC)

    result = check_and_record(session, client_answering(ok), monitor.id)

    assert result is not None
    assert (result.monitor_id, result.up, result.status_code, result.error) == (monitor.id, True, 200, None)
    assert before <= result.checked_at <= datetime.now(UTC)
    assert count_results(session) == 1


def test_records_a_down_result(session):
    monitor = add_monitor(session)

    result = check_and_record(session, client_answering(lambda r: httpx2.Response(503)), monitor.id)

    assert (result.up, result.status_code) == (False, 503)


def test_records_the_reason_when_no_response_arrived(session):
    monitor = add_monitor(session)

    def handler(request):
        raise httpx2.ConnectError("[Errno 111] Connection refused", request=request)

    result = check_and_record(session, client_answering(handler), monitor.id)

    assert (result.up, result.status_code, result.response_time_ms, result.error) == (
        False, None, None, "connection refused",
    )


def test_skips_a_deleted_monitor(session):
    assert check_and_record(session, client_answering(ok), 12345) is None
    assert count_results(session) == 0


def test_skips_a_paused_monitor(session):
    monitor = add_monitor(session, paused=True)

    assert check_and_record(session, client_answering(ok), monitor.id) is None
    assert count_results(session) == 0


def test_monitor_deleted_during_the_check_records_nothing(session, engine):
    monitor = add_monitor(session)

    def delete_then_answer(request):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM monitors WHERE id = :id"), {"id": monitor.id})
        return httpx2.Response(200)

    assert check_and_record(session, client_answering(delete_then_answer), monitor.id) is None
    assert count_results(session) == 0
