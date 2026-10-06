import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from methane_monitor.api.app import create_app
from methane_monitor.cli import run_smoke
from methane_monitor.detection import CUSUMDetector, ThresholdDetector
from methane_monitor.experiments.benchmark import run_benchmark
from methane_monitor.experiments.metrics import evaluate
from methane_monitor.ingestion.simulator import SimulatedSample, Simulator
from methane_monitor.models import AppConfig, ArtifactType, Scenario, SimulationConfig
from methane_monitor.pipeline import DetectionPipeline
from methane_monitor.processing import ExponentialMovingAverage, estimate_baseline
from methane_monitor.storage.sqlite import SQLiteStore


def cfg(**kwargs):
    values = {"samples": 60, "event_start": 10, "event_end": 30}
    values.update(kwargs)
    return SimulationConfig(**values)


def test_seed_reproducibility_and_difference():
    assert list(Simulator(cfg(seed=4))) == list(Simulator(cfg(seed=4)))
    assert list(Simulator(cfg(seed=4))) != list(Simulator(cfg(seed=5)))


def test_scenarios_and_ground_truth():
    assert not any(s.is_leak for s in Simulator(cfg(scenario=Scenario.STABLE)))
    assert sum(s.is_leak for s in Simulator(cfg(scenario=Scenario.SUDDEN_LEAK))) == 20
    assert sum(s.is_leak for s in Simulator(cfg(scenario=Scenario.GRADUAL_LEAK))) == 20
    assert any(s.is_leak for s in Simulator(cfg(scenario=Scenario.INTERMITTENT)))
    drift = list(Simulator(cfg(scenario=Scenario.DRIFT, drift_per_sample=0.25, noise_sigma=0)))
    assert not any(s.is_leak for s in drift)
    assert drift[-1].value - drift[0].value > 10
    assert all(s.artifact_type == ArtifactType.DRIFT for s in drift)
    outliers = list(Simulator(cfg(scenario=Scenario.OUTLIERS)))
    assert not any(s.is_leak for s in outliers) and any(s.artifact_type == ArtifactType.OUTLIER for s in outliers)
    assert any(s.artifact_type == ArtifactType.MISSING for s in Simulator(cfg(scenario=Scenario.MISSING)))
    assert any(s.artifact_type == ArtifactType.SATURATION for s in Simulator(cfg(scenario=Scenario.SATURATION)))


def test_invalid_scenarios_intervals_and_drift():
    with pytest.raises(ValueError): SimulationConfig(scenario="typo")
    with pytest.raises(ValueError): SimulationConfig(scenario=Scenario.DRIFT)
    with pytest.raises(ValueError): SimulationConfig(scenario=Scenario.LEAK, event_start=20, event_end=20)
    with pytest.raises(ValueError): SimulationConfig(scenario=Scenario.LEAK, event_end=61)
    with pytest.raises(ValueError): SimulationConfig(saturation_min=2, saturation_max=2)
    with pytest.raises(ValueError): AppConfig.model_validate({"simulation": {"samples": 2}, "detector": {"baseline_window_samples": 3}})


def test_processing_baseline_smoothing_and_nonfinite():
    baseline = estimate_baseline([1, 2, 3, 4])
    assert baseline.mean == 2.5 and baseline.sigma > 0
    assert estimate_baseline([1, 1, 1]).sigma > 0
    with pytest.raises(ValueError): estimate_baseline([1, float("nan")])
    ema = ExponentialMovingAverage(0.5)
    assert ema.update(2) == 2 and ema.update(4) == 3


def test_threshold_onset_and_release():
    detector = ThresholdDetector(10, 2)
    first, held, released = detector.update(10), detector.update(9), detector.update(7)
    assert first.alarm and first.triggered and held.alarm and not held.triggered and not released.alarm


def test_cusum_consecutive_crossings_are_distinct_triggers():
    baseline = estimate_baseline([0, 1])
    detector = CUSUMDetector(baseline, k=0, threshold=2)
    results = [detector.update(3) for _ in range(5)]
    assert all(result.alarm and result.triggered for result in results)
    assert sum(result.triggered for result in results) == 5
    metrics = evaluate([False, True, True, True, False], [False, True, True, True, False], [False, True, True, True, False])
    assert metrics["detector_triggers"] == 3 and metrics["matched_event_onsets"] == 1 and metrics["duplicate_event_onsets"] == 2


def test_stateful_alarm_has_one_trigger_for_persistent_alarm():
    detector = ThresholdDetector(10, 0)
    results = [detector.update(value) for value in [0, 11, 12, 13, 0]]
    assert [result.triggered for result in results] == [False, True, False, False, False]


def test_cusum_no_change_shift_and_reset():
    baseline = estimate_baseline([0, 0, 0, 0])
    detector = CUSUMDetector(baseline, k=0.5, threshold=3)
    assert not any(detector.update(0).alarm for _ in range(10))
    assert detector.update(2).alarm
    assert not detector.update(0).alarm


def test_metrics_late_duplicate_and_false_alarm_semantics():
    late = evaluate([False, False, True, True, False, False], [False, False, False, False, True, False])
    assert late["detected_events"] == 0 and late["missed_events"] == 1 and late["false_alarm_episodes"] == 1
    duplicate = evaluate([False, True, True, True, False], [False, True, False, True, False])
    assert duplicate["matched_event_onsets"] == 1
    assert duplicate["duplicate_event_onsets"] == 1
    assert duplicate["false_alarm_episodes"] == 0
    assert duplicate["false_alarm_episodes"] <= duplicate["false_positive_samples"]


def test_metrics_sample_confusion_and_multi_event():
    result = evaluate([False, True, True, False, False, True], [False, True, False, True, False, True])
    assert result["total_events"] == 2 and result["detected_events"] == 2
    assert result["true_positive_samples"] == 2 and result["false_positive_samples"] == 1
    assert result["sample_precision"] == pytest.approx(2 / 3)


def test_pipeline_baseline_uses_same_filter_state():
    config = AppConfig(simulation=cfg(seed=2), detector={"algorithm": "zscore", "preprocessing_smoothing_enabled": True, "preprocessing_smoothing_alpha": 0.5})
    samples = list(Simulator(config.simulation))
    pipeline = DetectionPipeline(config)
    pipeline.process(samples)
    expected_filter = ExponentialMovingAverage(0.5)
    processed = [expected_filter.update(s.value) for s in samples[:20] if s.value is not None]
    expected = estimate_baseline(processed)
    assert pipeline.baseline.mean == pytest.approx(expected.mean)
    assert pipeline.baseline.sigma == pytest.approx(expected.sigma)
    assert pipeline._smoother.value is not None


def test_pipeline_raw_baseline_parity():
    config = AppConfig(simulation=cfg(seed=2), detector={"algorithm": "zscore", "preprocessing_smoothing_enabled": False})
    samples = list(Simulator(config.simulation)); pipeline = DetectionPipeline(config); pipeline.process(samples)
    expected = estimate_baseline([s.value for s in samples[:20]])
    assert pipeline.baseline.mean == expected.mean and pipeline.baseline.sigma == expected.sigma


def test_benchmark_metadata_and_cusum_effective_parameters():
    config = AppConfig(simulation=cfg(), detector={"algorithm": "zscore"})
    results = run_benchmark(config, ["threshold", "cusum"])
    assert results[0]["algorithm"] == "threshold"
    assert results[0]["detector_parameters"] == {"threshold": 350.0, "hysteresis": 0.5}
    assert results[1]["algorithm"] == "cusum"
    assert set(results[1]["detector_parameters"]) == {"cusum_k", "cusum_h"}
    assert results[0]["simulation_config"]["sample_period"] == 1.0
    assert "drift_per_sample" in results[0]["simulation_config"]


def test_runtime_and_benchmark_share_pipeline():
    config = AppConfig(simulation=cfg(seed=9), detector={"algorithm": "zscore"})
    samples = list(Simulator(config.simulation)); runtime = DetectionPipeline(config).process(samples)
    benchmark = run_benchmark(config, ["zscore"])[0]
    assert benchmark["metrics"] == evaluate([s.is_leak for s in samples], runtime.alarm_states, runtime.trigger_mask)


def test_sqlite_round_trip_preserves_labels_and_missing_rows(tmp_path: Path):
    store = SQLiteStore(str(tmp_path / "test.db"))
    samples = [SimulatedSample(0, 0, 320, False), SimulatedSample(1, 1, 420, True), SimulatedSample(2, 2, None, False, ArtifactType.MISSING), SimulatedSample(3, 3, 1000, False, ArtifactType.OUTLIER)]
    config = AppConfig(simulation=cfg(samples=4, event_start=1, event_end=2), detector={"algorithm": "zscore", "baseline_window_samples": 2})
    run = DetectionPipeline(config, store=store).process(samples).run
    rows = {row["sample_index"]: row for row in store.readings(10)}
    assert set(rows) == {0, 1, 2, 3}
    assert rows[1]["is_leak"] == 1
    assert rows[2]["raw_value"] is None and rows[2]["filtered_value"] is None and rows[2]["artifact_type"] == "missing"
    assert rows[3]["artifact_type"] == "outlier"
    assert store.experiment(run.run_id)["source"] == "simulator"


def test_serial_metadata_is_not_simulation_metadata():
    config = AppConfig(simulation=cfg(), detector={"algorithm": "zscore"})
    samples = [SimulatedSample(i, i, float(i), False) for i in range(30)]
    run = DetectionPipeline(config, source="serial").process(samples).run
    assert run.source == "serial" and run.random_seed is None and run.scenario is None and run.simulation_config == {}


def test_smoke_explicit_drift_override():
    config = AppConfig(simulation=cfg())
    result = run_smoke(config, [1], [Scenario.DRIFT], 0.25)
    assert result["runs"][0]["drift_per_sample"] == 0.25
    assert result["runs"][0]["results"][0]["simulation_config"]["drift_per_sample"] == 0.25


def test_smoke_zero_drift_is_rejected():
    config = AppConfig(simulation=cfg())
    with pytest.raises(ValueError): run_smoke(config, [1], [Scenario.DRIFT], 0)


def test_smoke_zero_drift_cli_is_rejected(tmp_path: Path):
    completed = subprocess.run(["methane-monitor", "--config", "config.yaml", "smoke", "--seeds", "1", "--scenarios", "drift", "--drift-rate", "0", "--output", str(tmp_path / "zero.json")], capture_output=True, text=True)
    assert completed.returncode != 0


def test_pipeline_preserves_trigger_mask_and_versions():
    config = AppConfig(simulation=cfg(), detector={"algorithm": "cusum"})
    result = DetectionPipeline(config).process(Simulator(config.simulation))
    assert len(result.alarm_states) == len(result.trigger_mask) == config.simulation.samples
    assert result.run.metrics_version == "2.2" and result.run.schema_version == "2.2"
    assert result.run.preprocessing_config["baseline_window_samples"] == 20


def test_config_file_errors(tmp_path: Path):
    with pytest.raises(FileNotFoundError): AppConfig.from_yaml(str(tmp_path / "missing.yaml"))
    malformed = tmp_path / "bad.yaml"; malformed.write_text("simulation: [")
    with pytest.raises(ValueError): AppConfig.from_yaml(str(malformed))


def test_api_round_trip_and_missing_experiment(tmp_path: Path):
    db = tmp_path / "api.db"; store = SQLiteStore(str(db))
    config = AppConfig(simulation=cfg(), detector={"algorithm": "zscore"})
    run = DetectionPipeline(config, store=store).process(Simulator(config.simulation)).run
    client = TestClient(create_app(str(db)))
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/readings").status_code == 200
    assert client.get(f"/experiments/{run.run_id}").status_code == 200
    assert client.get("/experiments/missing").status_code == 404
