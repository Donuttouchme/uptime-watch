import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from rq import SimpleWorker
from sqlalchemy import select

from uptime_watch.models import Monitor, Result
from uptime_watch.scheduler import enqueue_due


class _Ok(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


@pytest.fixture
def local_site():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Ok)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    server.server_close()


def test_a_due_monitor_is_checked_and_its_result_stored(
    session, queue, redis_conn, local_site, app_uses_test_database
):
    monitor = Monitor(name="Local site", url=local_site)
    session.add(monitor)
    session.commit()

    assert enqueue_due(session, queue) == [monitor.id]
    # SimpleWorker runs jobs in this process; burst mode exits when the queue is empty.
    SimpleWorker([queue], connection=redis_conn).work(burst=True)

    session.expire_all()
    [result] = session.scalars(select(Result)).all()
    assert result.monitor_id == monitor.id
    assert (result.up, result.status_code, result.error) == (True, 200, None)
    assert result.response_time_ms >= 0
