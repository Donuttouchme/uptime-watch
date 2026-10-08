# One repository, one backend package

Everything lives in one repository: the Python backend in `backend/` and the React frontend in `web/`. One README tells the whole story, and a change that spans the backend and the frontend lands in one pull request. CI runs only the jobs whose folders changed (path filters).

The api, scheduler and worker are **one Python package with three entry points**, not three projects. They share the same models and database code, and later they ship as one container image started with three different commands.

## Considered options

- **Separate repositories** (`uptime-watch-api`, `uptime-watch-web`): rejected. They need separate pipelines and coordinated versioning, which is more overhead than a one-person project gains.
- **A folder per process** (`api/`, `scheduler/`, `worker/`) with a shared library: rejected. Three dependency sets and three images for code that shares its whole data model.
