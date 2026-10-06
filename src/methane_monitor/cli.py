from __future__ import annotations

import argparse
import json
from itertools import islice
from pathlib import Path

from methane_monitor.api.app import create_app
from methane_monitor.experiments import run_benchmark, save_results
from methane_monitor.ingestion.serial import SerialSource
from methane_monitor.ingestion.simulator import Simulator
from methane_monitor.models import AppConfig, Scenario, SimulationConfig
from methane_monitor.pipeline import DetectionPipeline
from methane_monitor.storage.sqlite import SQLiteStore


def run_smoke(config: AppConfig, seeds: list[int], scenarios: list[Scenario], drift_rate: float) -> dict:
    runs = []
    for seed in seeds:
        for scenario in scenarios:
            simulation = SimulationConfig.model_validate({**config.simulation.model_dump(), "seed": seed, "scenario": scenario, "drift_per_sample": drift_rate if scenario == Scenario.DRIFT else config.simulation.drift_per_sample})
            experiment_config = AppConfig.model_validate({**config.model_dump(), "simulation": simulation.model_dump()})
            benchmark = run_benchmark(experiment_config)
            runs.append({"seed": seed, "scenario": scenario.value, "drift_per_sample": simulation.drift_per_sample, "results": benchmark})
    summary = []
    for scenario in scenarios:
        for algorithm in ["threshold", "zscore", "ewma", "cusum"]:
            rows = [entry["results"] for entry in runs if entry["scenario"] == scenario.value]
            metrics = [next(item["metrics"] for item in row if item["algorithm"] == algorithm) for row in rows]
            summary.append({"scenario": scenario.value, "algorithm": algorithm, "detected_events": [m["detected_events"] for m in metrics], "event_detection_rate": [m["event_detection_rate"] for m in metrics], "mean_detection_delay": [m["mean_detection_delay"] for m in metrics], "false_alarm_episodes": [m["false_alarm_episodes"] for m in metrics], "duplicate_event_onsets": [m["duplicate_event_onsets"] for m in metrics], "false_positive_sample_rate": [m["false_positive_sample_rate"] for m in metrics], "time_in_alarm_fraction": [m["time_in_alarm_fraction"] for m in metrics]})
    return {"schema_version": "2.2-smoke", "seeds": seeds, "scenarios": [s.value for s in scenarios], "drift_per_sample": drift_rate, "runs": runs, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(prog="methane-monitor"); parser.add_argument("--config", default="config.yaml", help="YAML configuration; missing files fail")
    sub = parser.add_subparsers(dest="command", required=True)
    simulate = sub.add_parser("simulate"); simulate.add_argument("--database", default=None)
    benchmark = sub.add_parser("benchmark"); benchmark.add_argument("--output", default="results/benchmark.json")
    smoke = sub.add_parser("smoke"); smoke.add_argument("--seeds", nargs="+", type=int, default=[1, 7, 19, 42, 101]); smoke.add_argument("--scenarios", nargs="+", choices=[s.value for s in Scenario], default=["stable", "sudden_leak", "gradual_leak", "drift"]); smoke.add_argument("--drift-rate", type=float, default=0.25); smoke.add_argument("--output", default="results/multi_seed_smoke.json")
    run = sub.add_parser("run"); run.add_argument("--source", choices=["serial"], required=True); run.add_argument("--port", required=True); run.add_argument("--baud", type=int, default=9600)
    api = sub.add_parser("api"); api.add_argument("--host", default="0.0.0.0"); api.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try: config = AppConfig.from_yaml(args.config)
    except (FileNotFoundError, ValueError) as exc: parser.error(str(exc))
    if args.command == "simulate":
        store = SQLiteStore(args.database or config.database_url); result = DetectionPipeline(config, store=store).process(Simulator(config.simulation)); store.close(); print(result.run.model_dump_json(indent=2)); return 0
    if args.command == "benchmark":
        results = run_benchmark(config); save_results(results, args.output); print(json.dumps(results, indent=2)); return 0
    if args.command == "smoke":
        result = run_smoke(config, args.seeds, [Scenario(s) for s in args.scenarios], args.drift_rate); path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(result, indent=2) + "\n"); print(json.dumps(result["summary"], indent=2)); return 0
    if args.command == "run":
        source = SerialSource(args.port, args.baud, sample_period=config.simulation.sample_period); result = DetectionPipeline(config, source="serial").process(islice(source, config.simulation.samples)); print(result.run.model_dump_json(indent=2)); return 0
    import uvicorn
    uvicorn.run(create_app(config.database_url), host=args.host, port=args.port); return 0


if __name__ == "__main__": raise SystemExit(main())
