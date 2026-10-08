from fastapi import FastAPI

app = FastAPI(title="uptime-watch")


@app.get("/health")
def health() -> dict[str, str]:
    # Liveness only: answers as long as the process runs, without touching the database.
    return {"status": "ok"}
