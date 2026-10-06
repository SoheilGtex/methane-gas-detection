from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass

from methane_monitor.detection import build_detector
from methane_monitor.ingestion.simulator import SimulatedSample
from methane_monitor.models import DetectionEvent, ExperimentRun, SensorReading
from methane_monitor.processing import ExponentialMovingAverage, estimate_baseline
from methane_monitor.storage.sqlite import SQLiteStore


def git_metadata() -> tuple[str | None, bool | None]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.SubprocessError): return None, None


@dataclass(frozen=True)
class PipelineResult:
    run: ExperimentRun
    alarm_states: list[bool]
    trigger_mask: list[bool]


class DetectionPipeline:
    def __init__(self, config, *, store: SQLiteStore | None = None, run: ExperimentRun | None = None, source: str = "simulator"):
        self.config, self.store, self.run, self.source = config, store, run, source
        self.samples: list[SimulatedSample] = []
        self._smoother = ExponentialMovingAverage(config.detector.preprocessing_smoothing_alpha) if config.detector.preprocessing_smoothing_enabled else None

    def process(self, samples: Iterable[SimulatedSample]) -> PipelineResult:
        self.samples = list(samples); detector_config = self.config.detector; n = detector_config.baseline_window_samples
        processed_baseline: list[float] = []; processed_values: list[float | None] = [None] * len(self.samples)
        for sample in self.samples[:n]:
            if sample.value is None: continue
            filtered = self._preprocess(sample.value); processed_values[sample.sample_index] = filtered; processed_baseline.append(filtered)
        if len(processed_baseline) < 2: raise ValueError("not enough finite processed samples for baseline estimation")
        baseline = estimate_baseline(processed_baseline); self.baseline = baseline
        commit, dirty = git_metadata()
        self.run = self.run or ExperimentRun(source=self.source, random_seed=self.config.simulation.seed if self.source == "simulator" else None, scenario=self.config.simulation.scenario if self.source == "simulator" else None, simulation_config=self.config.simulation.model_dump(mode="json") if self.source == "simulator" else {}, algorithm=detector_config.algorithm, preprocessing_config={"smoothing_enabled": detector_config.preprocessing_smoothing_enabled, "smoothing_alpha": detector_config.preprocessing_smoothing_alpha, "baseline_window_samples": n}, detector_parameters=self._effective_parameters(), git_commit=commit, git_dirty=dirty)
        detector = build_detector(detector_config.algorithm, baseline, threshold=detector_config.threshold, z_threshold=detector_config.z_threshold, ewma_alpha=detector_config.detector_ewma_alpha, cusum_k=detector_config.cusum_k, cusum_h=detector_config.cusum_h, hysteresis=detector_config.hysteresis)
        alarms = [False] * len(self.samples); triggers = [False] * len(self.samples)
        for sample in self.samples[n:]:
            filtered = None if sample.value is None else self._preprocess(sample.value); processed_values[sample.sample_index] = filtered
            if self.store: self._save_reading(sample, filtered)
            if filtered is None: continue
            result = detector.update(filtered); alarms[sample.sample_index] = result.alarm; triggers[sample.sample_index] = result.triggered
            if self.store and result.triggered:
                self.store.save_event(DetectionEvent(sample_index=sample.sample_index, simulated_time=sample.simulated_time, sensor_id="sensor", algorithm=result.algorithm, score=result.score, threshold=result.threshold, state="onset", run_id=self.run.run_id))
        for sample in self.samples[:n]:
            if self.store: self._save_reading(sample, processed_values[sample.sample_index])
        if self.store: self.store.save_experiment(self.run)
        return PipelineResult(self.run, alarms, triggers)

    def _preprocess(self, value: float) -> float: return self._smoother.update(value) if self._smoother else value

    def _save_reading(self, sample: SimulatedSample, filtered: float | None) -> None:
        self.store.save_reading(SensorReading(sample_index=sample.sample_index, simulated_time=sample.simulated_time, raw_value=sample.value, filtered_value=filtered, is_leak=sample.is_leak if self.source == "simulator" else None, artifact_type=sample.artifact_type if self.source == "simulator" else None, source=self.source, run_id=self.run.run_id))

    def _effective_parameters(self) -> dict:
        d = self.config.detector
        if d.algorithm == "threshold": return {"threshold": d.threshold, "hysteresis": d.hysteresis}
        if d.algorithm == "zscore": return {"z_threshold": d.z_threshold, "hysteresis": d.hysteresis}
        if d.algorithm == "ewma": return {"z_threshold": d.z_threshold, "detector_ewma_alpha": d.detector_ewma_alpha, "hysteresis": d.hysteresis}
        return {"cusum_k": d.cusum_k, "cusum_h": d.cusum_h}
