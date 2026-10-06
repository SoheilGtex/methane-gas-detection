from __future__ import annotations

import json
from pathlib import Path

from methane_monitor.experiments.metrics import evaluate
from methane_monitor.ingestion.simulator import Simulator
from methane_monitor.models import AppConfig
from methane_monitor.pipeline import DetectionPipeline


def run_benchmark(config: AppConfig, algorithms: list[str] | None = None) -> list[dict]:
    names = algorithms or ["threshold", "zscore", "ewma", "cusum"]
    results = []
    for algorithm in names:
        detector_config = config.detector.model_copy(update={"algorithm": algorithm})
        experiment_config = AppConfig.model_validate({**config.model_dump(), "detector": detector_config.model_dump()})
        samples = list(Simulator(experiment_config.simulation)); result = DetectionPipeline(experiment_config).process(samples)
        result.run.metrics = evaluate([s.is_leak for s in samples], result.alarm_states, result.trigger_mask, sample_period=config.simulation.sample_period)
        results.append(result.run.model_dump(mode="json"))
    return results


def save_results(results: list[dict], path: str = "results/benchmark.json") -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
