# Schema changes go through Alembic migrations

Every change to the database schema is a numbered Alembic migration, applied with `alembic upgrade head`; the app never creates or alters tables at startup. `create_all()` can create missing tables but cannot change existing ones, so the first new column would have stuck us.

## Consequences

- Running migrations is a deployment step of its own, not part of app startup. Each platform (systemd, Compose, CI, Kubernetes) needs an answer to "when do migrations run, and what if two copies start at once?"
