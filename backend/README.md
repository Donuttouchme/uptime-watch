# uptime-watch backend

The Python package behind the api, scheduler and worker. See the repository README for how to run it.

## Adding a migration

Migrations are numbered (see ADR 0004), but Alembic generates hex ids by default. Pass the next free four-digit number as the revision id:

```bash
uv run alembic revision -m "short description" --rev-id 0002
```

The file comes out as `migrations/versions/0002_short_description.py`, matching `0001_create_monitors.py`.
