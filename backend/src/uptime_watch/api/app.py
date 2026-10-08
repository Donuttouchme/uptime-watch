from fastapi import FastAPI

from uptime_watch.api.monitors import router as monitors_router

app = FastAPI(title="uptime-watch")
app.include_router(monitors_router)


@app.get("/health")
def health() -> dict[str, str]:
    # Liveness only: answers as long as the process runs, without touching the database.
    return {"status": "ok"}
