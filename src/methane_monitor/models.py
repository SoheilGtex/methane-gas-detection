from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class Scenario(StrEnum):
    STABLE = "stable"
    LEAK = "leak"
    SUDDEN_LEAK = "sudden_leak"
    GRADUAL_LEAK = "gradual_leak"
    INTERMITTENT = "intermittent"
    DRIFT = "drift"
    OUTLIERS = "outliers"
    MISSING = "missing"
    SATURATION = "saturation"


class ArtifactType(StrEnum):
    NONE = "none"
    OUTLIER = "outlier"
    MISSING = "missing"
    DRIFT = "drift"
    SATURATION = "saturation"


def utc_now() -> datetime: return datetime.now(UTC)


class SensorReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_index: int = Field(ge=0)
    simulated_time: float = Field(ge=0)
    timestamp: datetime = Field(default_factory=utc_now)
    sensor_id: str = "sensor"
    raw_value: float | None = None
    filtered_value: float | None = None
    is_leak: bool | None = None
    artifact_type: ArtifactType | None = None
    source: Literal["simulator", "serial"] = "simulator"
    run_id: str | None = None


class DetectionEvent(BaseModel):
    sample_index: int = Field(ge=0)
    simulated_time: float = Field(ge=0)
    timestamp: datetime = Field(default_factory=utc_now)
    sensor_id: str
    algorithm: str
    score: float
    threshold: float
    state: Literal["active", "onset", "release"]
    run_id: str | None = None


class ExperimentRun(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    source: Literal["simulator", "serial"]
    random_seed: int | None = None
    scenario: Scenario | None = None
    simulation_config: dict[str, Any] = Field(default_factory=dict)
    algorithm: str
    preprocessing_config: dict[str, Any]
    detector_parameters: dict[str, Any]
    git_commit: str | None = None
    git_dirty: bool | None = None
    started_at: datetime = Field(default_factory=utc_now)
    schema_version: str = "2.2"
    metrics_version: str = "2.2"
    metrics: dict[str, float | int | None] = Field(default_factory=dict)


class SimulationConfig(BaseModel):
    scenario: Scenario = Scenario.LEAK
    seed: int = 7
    samples: int = Field(300, gt=0)
    sample_period: float = Field(1.0, gt=0)
    baseline: float = 320.0
    noise_sigma: float = Field(6.0, ge=0)
    drift_per_sample: float = 0.0
    event_start: int = Field(100, ge=0)
    event_end: int = Field(180, ge=0)
    event_amplitude: float = 100.0
    missing_rate: float = Field(0.0, ge=0, le=1)
    outlier_rate: float = Field(0.0, ge=0, le=1)
    saturation_min: float = 0.0
    saturation_max: float = 1023.0

    @model_validator(mode="after")
    def validate_ranges(self) -> SimulationConfig:
        if self.saturation_min >= self.saturation_max: raise ValueError("saturation_min must be less than saturation_max")
        if self.scenario == Scenario.DRIFT and self.drift_per_sample == 0: raise ValueError("drift_per_sample must be non-zero for the drift scenario")
        event_scenarios = {Scenario.LEAK, Scenario.SUDDEN_LEAK, Scenario.GRADUAL_LEAK, Scenario.INTERMITTENT}
        if self.scenario in event_scenarios:
            if self.event_start >= self.event_end: raise ValueError("event_start must be less than event_end for event scenarios")
            if self.event_end > self.samples: raise ValueError("event_end must be no greater than samples")
        return self


class DetectorConfig(BaseModel):
    algorithm: Literal["threshold", "zscore", "ewma", "cusum"] = "zscore"
    threshold: float = 350.0
    z_threshold: float = 3.0
    detector_ewma_alpha: float = Field(0.2, gt=0, le=1)
    cusum_k: float = Field(0.5, ge=0)
    cusum_h: float = Field(5.0, gt=0)
    hysteresis: float = Field(0.5, ge=0)
    baseline_window_samples: int = Field(20, ge=2, validation_alias=AliasChoices("baseline_window_samples", "min_baseline_samples"))
    preprocessing_smoothing_enabled: bool = True
    preprocessing_smoothing_alpha: float = Field(0.2, gt=0, le=1)


class AppConfig(BaseModel):
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    database_url: str = "sqlite:///results/methane_monitor.db"

    @model_validator(mode="after")
    def validate_cross_fields(self) -> AppConfig:
        if self.detector.baseline_window_samples > self.simulation.samples: raise ValueError("baseline_window_samples must not exceed simulation.samples")
        return self

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> AppConfig:
        from pathlib import Path

        import yaml
        p = Path(path)
        if not p.exists(): raise FileNotFoundError(f"configuration file does not exist: {path}")
        try: data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc: raise ValueError(f"malformed YAML configuration: {path}") from exc
        try: return cls.model_validate(data or {})
        except Exception as exc: raise ValueError(f"invalid configuration in {path}: {exc}") from exc
