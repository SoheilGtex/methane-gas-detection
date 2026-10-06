from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass

from methane_monitor.models import ArtifactType, Scenario, SimulationConfig


@dataclass(frozen=True)
class SimulatedSample:
    sample_index: int
    simulated_time: float
    value: float | None
    is_leak: bool
    artifact_type: ArtifactType = ArtifactType.NONE
    event_id: str | None = None


class Simulator:
    """Seeded synthetic stream; leak labels are separate from nuisance artifacts."""

    def __init__(self, config: SimulationConfig):
        self.config = config

    def __iter__(self) -> Iterator[SimulatedSample]:
        c = self.config
        rng = random.Random(c.seed)
        for i in range(c.samples):
            value = c.baseline + c.drift_per_sample * i
            is_leak = False
            artifact = ArtifactType.DRIFT if c.scenario == Scenario.DRIFT else ArtifactType.NONE
            if c.scenario in {Scenario.LEAK, Scenario.SUDDEN_LEAK} and c.event_start <= i < c.event_end:
                value += c.event_amplitude
                is_leak = True
            elif c.scenario == Scenario.GRADUAL_LEAK and c.event_start <= i < c.event_end:
                value += c.event_amplitude * (i - c.event_start) / max(1, c.event_end - c.event_start - 1)
                is_leak = True
            elif c.scenario == Scenario.INTERMITTENT and c.event_start <= i < c.event_end:
                is_leak = (i - c.event_start) % 10 < 4
                value += c.event_amplitude if is_leak else 0
            outlier_rate = 0.05 if c.scenario == Scenario.OUTLIERS and c.outlier_rate == 0 else c.outlier_rate
            if rng.random() < outlier_rate:
                value += rng.choice((-1, 1)) * c.event_amplitude * 2
                artifact = ArtifactType.OUTLIER
            value += rng.gauss(0, c.noise_sigma)
            if c.scenario == Scenario.SATURATION:
                value = c.saturation_max + abs(rng.gauss(0, max(1, c.noise_sigma)))
            clipped = max(c.saturation_min, min(c.saturation_max, value))
            if clipped != value:
                artifact = ArtifactType.SATURATION
            missing = c.scenario == Scenario.MISSING and i % 17 == 0 or rng.random() < c.missing_rate
            if missing:
                yield SimulatedSample(i, i * c.sample_period, None, is_leak, ArtifactType.MISSING, "synthetic-leak" if is_leak else None)
            else:
                yield SimulatedSample(i, i * c.sample_period, clipped, is_leak, artifact, "synthetic-leak" if is_leak else None)
