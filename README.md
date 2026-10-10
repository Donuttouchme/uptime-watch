# uptime-watch

A small uptime monitor: register URLs, and uptime-watch checks them on a schedule and records whether each one is up and how fast it answers.

## Why this exists

This is my DevOps learning capstone. The app is deliberately small; the point is the platform around it. Every few weeks a new layer goes on top of the same app, and this README records each one.

## Architecture

```
            ┌──────────┐    jobs     ┌─────────┐
 scheduler ─┤  Redis   ├────────────►│ worker  │──HTTP GET──► monitored URLs
  (×1)      └──────────┘             │ (×1..n) │
                                     └────┬────┘
 web (React) ──► api (FastAPI) ◄──────────┘ results
                      │
                  PostgreSQL ──► /metrics ──► Prometheus
```

- **api**: FastAPI. Manages monitors and serves results.
- **scheduler**: decides when each monitor is due and puts a job on the queue. Runs as exactly one copy.
- **worker**: takes jobs from the queue and runs the checks. Scales out.
- **web**: React + Vite + TypeScript frontend.
- **PostgreSQL** stores monitors and results; **Redis** is the job queue.

### How a check travels

1. Every 5 seconds (`SCHEDULER_TICK_SECONDS`) the **scheduler** asks Postgres which monitors are due, moves each one's `next_check_at` one interval ahead, and pushes a job onto the Redis list `rq:queue:checks`. The list holds only the job ID; the details sit in a hash `rq:job:<id>` that expires after one interval, because a check that waited longer is stale and a newer one is already queued.
2. A **worker** moves the ID to `rq:queue:checks:intermediate` (so a crash mid-check doesn't lose it), runs the HTTP GET, and writes the result to **Postgres**. IDs whose hash has expired are dropped without a log line.
3. The **api** reads monitors and results from Postgres only; it never talks to Redis. With Redis down, the API still answers and checks simply pause; with Postgres down, every part fails.

Design decisions are recorded in [`docs/adr/`](docs/adr/), and the project's vocabulary is in [`CONTEXT.md`](CONTEXT.md).

## Planned layers

| Layer | Status |
|---|---|
| App runs locally (Ubuntu on WSL 2) | in progress |
| systemd services | planned |
| Nginx reverse proxy + TLS | planned |
| Docker + Docker Compose | planned |
| CI/CD (GitHub Actions) | planned |
| Azure deployment | planned |
| Terraform | planned |
| Kubernetes | planned |
| Monitoring (Prometheus, Grafana, Alertmanager) | planned |
| GitOps | planned |

## Run locally

Requirements: Ubuntu (or WSL 2), PostgreSQL, Redis, [uv](https://docs.astral.sh/uv/).

```bash
cd backend
sudo -u postgres createuser --pwprompt uptime_watch          # a letters-and-digits password
sudo -u postgres createdb -O uptime_watch uptime_watch
sudo -u postgres createdb -O uptime_watch uptime_watch_test  # used by the tests
sudo apt install redis-server                                # listens on 127.0.0.1:6379
cp .env.example .env        # then put your database password into .env
uv sync                     # install the locked dependencies
uv run alembic upgrade head # create or upgrade the database schema
```

Then start the three processes, each in its own terminal (from `backend/`):

```bash
uv run uvicorn uptime_watch.api.app:app --reload   # api
uv run uptime-watch-scheduler                       # exactly one copy
uv run uptime-watch-worker                          # one or more copies
```

- Health: http://localhost:8000/health
- Interactive API docs: http://localhost:8000/docs
- A monitor's results: `GET /api/v1/monitors/{id}/results`
- Tests: `uv run pytest` (needs Postgres and Redis running; uses the `_test` database and Redis database 15)

## Status

Week 0: the app runs locally. Monitors are checked on their interval by a scheduler, a Redis queue and workers, and the results are served by the API.
