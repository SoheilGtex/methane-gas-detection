from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from methane_monitor.storage.sqlite import SQLiteStore


def create_app(database_path: str = "results/methane_monitor.db") -> FastAPI:
    app = FastAPI(title="Methane Monitoring API", version="0.2.0")
    store = SQLiteStore(database_path)

    @app.get("/health")
    def health() -> dict[str, str]: return {"status": "ok"}

    @app.get("/readings")
    def readings(limit: int = Query(100, ge=1, le=1000)) -> list[dict]: return store.readings(limit)

    @app.get("/events")
    def events(limit: int = Query(100, ge=1, le=1000)) -> list[dict]: return store.events(limit)

    @app.get("/experiments/{run_id}")
    def experiment(run_id: str) -> dict:
        result = store.experiment(run_id)
        if result is None: raise HTTPException(status_code=404, detail=f"experiment not found: {run_id}")
        return result

    return app


app = create_app()
