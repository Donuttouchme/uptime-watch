# uptime-watch backend

The Python package behind the api, scheduler and worker. See the repository README for how to run it.

## Adding a migration

Migrations are numbered (see ADR 0004), but Alembic generates hex ids by default. Pass the next free four-digit number as the revision id:

```bash
uv run alembic revision -m "short description" --rev-id 0002
```

The file comes out as `migrations/versions/0002_short_description.py`, matching `0001_create_monitors.py`.

## Settings

All settings are environment variables; `.env` is a local convenience (see `.env.example`).

| Variable | Default | Used by |
|---|---|---|
| `DATABASE_URL` | (required) | all |
| `REDIS_URL` | `redis://localhost:6379/0` | scheduler, worker |
| `SCHEDULER_TICK_SECONDS` | `5` | scheduler: how often it looks for due monitors |
| `CHECK_TIMEOUT_SECONDS` | `10` | worker: how long a check waits for the response headers |
| `TEST_DATABASE_URL` | (required for tests) | tests; the name must end in `_test` |
| `TEST_REDIS_URL` | `redis://localhost:6379/15` | tests; must be database 15 |
