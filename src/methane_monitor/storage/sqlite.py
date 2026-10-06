from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from methane_monitor.models import DetectionEvent, ExperimentRun, SensorReading

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    sample_index INTEGER NOT NULL, simulated_time REAL NOT NULL, timestamp TEXT NOT NULL,
    sensor_id TEXT NOT NULL, raw_value REAL, filtered_value REAL, is_leak INTEGER,
    artifact_type TEXT, source TEXT NOT NULL, run_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_readings_run ON readings(run_id);
CREATE TABLE IF NOT EXISTS events (
    sample_index INTEGER NOT NULL, simulated_time REAL NOT NULL, timestamp TEXT NOT NULL,
    sensor_id TEXT NOT NULL, algorithm TEXT NOT NULL, score REAL NOT NULL,
    threshold REAL NOT NULL, state TEXT NOT NULL, run_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
CREATE TABLE IF NOT EXISTS experiments (
    run_id TEXT PRIMARY KEY, source TEXT NOT NULL, random_seed INTEGER,
    scenario TEXT, simulation_config TEXT NOT NULL, preprocessing_config TEXT NOT NULL,
    detector_parameters TEXT NOT NULL, git_commit TEXT, git_dirty INTEGER,
    started_at TEXT NOT NULL, schema_version TEXT NOT NULL, metrics_version TEXT NOT NULL,
    metrics TEXT NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, path: str = "results/methane_monitor.db"):
        self.path = path.removeprefix("sqlite:///")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection: connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path); connection.row_factory = sqlite3.Row; return connection

    def save_reading(self, reading: SensorReading) -> None:
        with self._connect() as c:
            c.execute("INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (reading.sample_index, reading.simulated_time, reading.timestamp.isoformat(), reading.sensor_id, reading.raw_value, reading.filtered_value, reading.is_leak, reading.artifact_type.value if reading.artifact_type else None, reading.source, reading.run_id))

    def save_event(self, event: DetectionEvent) -> None:
        with self._connect() as c:
            c.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (event.sample_index, event.simulated_time, event.timestamp.isoformat(), event.sensor_id, event.algorithm, event.score, event.threshold, event.state, event.run_id))

    def save_experiment(self, run: ExperimentRun) -> None:
        with self._connect() as c:
            c.execute("INSERT OR REPLACE INTO experiments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run.run_id, run.source, run.random_seed, run.scenario.value if run.scenario else None, json.dumps(run.simulation_config), json.dumps(run.preprocessing_config), json.dumps(run.detector_parameters), run.git_commit, run.git_dirty, run.started_at.isoformat(), run.schema_version, run.metrics_version, json.dumps(run.metrics)))

    def readings(self, limit: int = 100) -> list[dict]:
        with self._connect() as c: return [dict(r) for r in c.execute("SELECT * FROM readings ORDER BY sample_index DESC LIMIT ?", (limit,))]

    def events(self, limit: int = 100) -> list[dict]:
        with self._connect() as c: return [dict(r) for r in c.execute("SELECT * FROM events ORDER BY sample_index DESC LIMIT ?", (limit,))]

    def experiment(self, run_id: str) -> dict | None:
        with self._connect() as c: row = c.execute("SELECT * FROM experiments WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def close(self) -> None: pass
