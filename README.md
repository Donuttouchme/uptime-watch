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

Requirements: Ubuntu (or WSL 2), PostgreSQL, [uv](https://docs.astral.sh/uv/).

```bash
cd backend
cp .env.example .env        # then put your database password into .env
uv sync                     # install the locked dependencies
uv run alembic upgrade head # create or upgrade the database schema
uv run uvicorn uptime_watch.api.app:app --reload
```

- Health: http://localhost:8000/health
- Interactive API docs: http://localhost:8000/docs
- Tests: `uv run pytest`

## Status

Week 0: the API runs locally. Monitors can be created, listed, updated and deleted; the checks themselves come next.
