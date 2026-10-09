from datetime import UTC, datetime, timedelta

from uptime_watch.models import Monitor, Result

MONITORS = "/api/v1/monitors"


def add_monitor(session, url="https://example.com/"):
    monitor = Monitor(name="Example", url=url)
    session.add(monitor)
    session.commit()
    return monitor


def add_results(session, monitor, count):
    start = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
    for minute in range(count):
        session.add(
            Result(
                monitor_id=monitor.id,
                checked_at=start + timedelta(minutes=minute),
                up=True,
                status_code=200,
                response_time_ms=10 + minute,
            )
        )
    session.commit()


def test_results_of_unknown_monitor_return_404(client):
    response = client.get(f"{MONITORS}/999/results")

    assert response.status_code == 404
    assert response.json() == {"detail": "Monitor not found"}


def test_results_empty(client, session):
    monitor = add_monitor(session)

    response = client.get(f"{MONITORS}/{monitor.id}/results")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_results_are_newest_first_and_paged(client, session):
    monitor = add_monitor(session)
    add_results(session, monitor, 3)

    first = client.get(f"{MONITORS}/{monitor.id}/results", params={"limit": 2}).json()
    rest = client.get(f"{MONITORS}/{monitor.id}/results", params={"limit": 2, "offset": 2}).json()

    assert first["total"] == 3
    assert [r["response_time_ms"] for r in first["items"]] == [12, 11]
    assert [r["response_time_ms"] for r in rest["items"]] == [10]


def test_results_belong_to_their_monitor_only(client, session):
    mine = add_monitor(session)
    other = add_monitor(session, url="https://example.org/")
    add_results(session, other, 2)

    body = client.get(f"{MONITORS}/{mine.id}/results").json()

    assert body["total"] == 0


def test_result_fields(client, session):
    monitor = add_monitor(session)
    session.add(
        Result(
            monitor_id=monitor.id,
            checked_at=datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
            up=False,
            error="timeout",
        )
    )
    session.commit()

    item = client.get(f"{MONITORS}/{monitor.id}/results").json()["items"][0]

    assert item["monitor_id"] == monitor.id
    assert item["up"] is False
    assert item["status_code"] is None
    assert item["response_time_ms"] is None
    assert item["error"] == "timeout"


def test_results_limit_must_be_between_1_and_200(client, session):
    monitor = add_monitor(session)

    assert client.get(f"{MONITORS}/{monitor.id}/results", params={"limit": 0}).status_code == 422
    assert client.get(f"{MONITORS}/{monitor.id}/results", params={"limit": 201}).status_code == 422
