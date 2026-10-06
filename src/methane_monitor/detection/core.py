from __future__ import annotations

from dataclasses import dataclass

from methane_monitor.processing import Baseline


@dataclass(frozen=True)
class DetectorResult:
    algorithm: str
    score: float
    threshold: float
    alarm: bool
    triggered: bool


class Hysteresis:
    def __init__(self, margin: float = 0.0):
        if margin < 0: raise ValueError("hysteresis margin cannot be negative")
        self.margin, self.active = margin, False

    def update(self, score: float, threshold: float) -> tuple[bool, bool]:
        previous = self.active
        if not self.active and score >= threshold: self.active = True
        elif self.active and score < threshold - self.margin: self.active = False
        return self.active, not previous and self.active


class ThresholdDetector:
    name = "threshold"
    def __init__(self, threshold: float, hysteresis: float = 0.0): self.threshold, self.state = threshold, Hysteresis(hysteresis)
    def update(self, value: float) -> DetectorResult:
        alarm, triggered = self.state.update(value, self.threshold)
        return DetectorResult(self.name, value, self.threshold, alarm, triggered)


class ZScoreDetector:
    name = "zscore"
    def __init__(self, baseline: Baseline, threshold: float = 3.0, hysteresis: float = 0.0): self.baseline, self.threshold, self.state = baseline, threshold, Hysteresis(hysteresis)
    def update(self, value: float) -> DetectorResult:
        score = (value - self.baseline.mean) / self.baseline.sigma
        alarm, triggered = self.state.update(score, self.threshold)
        return DetectorResult(self.name, score, self.threshold, alarm, triggered)


class EWMADetector:
    name = "ewma"
    def __init__(self, baseline: Baseline, alpha: float = 0.2, threshold: float = 3.0, hysteresis: float = 0.0):
        if not 0 < alpha <= 1: raise ValueError("alpha must be in (0, 1]")
        self.baseline, self.alpha, self.threshold, self.state = baseline, alpha, threshold, Hysteresis(hysteresis)
        self.level = baseline.mean
    def update(self, value: float) -> DetectorResult:
        self.level = self.alpha * value + (1 - self.alpha) * self.level
        score = (self.level - self.baseline.mean) / self.baseline.sigma
        alarm, triggered = self.state.update(score, self.threshold)
        return DetectorResult(self.name, score, self.threshold, alarm, triggered)


class CUSUMDetector:
    """One-sided signal-and-reset CUSUM; every crossing is an independent trigger."""
    name = "cusum"
    def __init__(self, baseline: Baseline, k: float = 0.5, threshold: float = 5.0):
        if k < 0 or threshold <= 0: raise ValueError("CUSUM k must be non-negative and threshold positive")
        self.baseline, self.k, self.threshold, self.cumulative = baseline, k, threshold, 0.0
    def update(self, value: float) -> DetectorResult:
        standardized = (value - self.baseline.mean) / self.baseline.sigma
        self.cumulative = max(0.0, self.cumulative + standardized - self.k)
        triggered = self.cumulative >= self.threshold
        score = self.cumulative
        if triggered: self.cumulative = 0.0
        return DetectorResult(self.name, score, self.threshold, triggered, triggered)


def build_detector(name: str, baseline: Baseline, *, threshold: float, z_threshold: float, ewma_alpha: float, cusum_k: float, cusum_h: float, hysteresis: float):
    if name == "threshold": return ThresholdDetector(threshold, hysteresis)
    if name == "zscore": return ZScoreDetector(baseline, z_threshold, hysteresis)
    if name == "ewma": return EWMADetector(baseline, ewma_alpha, z_threshold, hysteresis)
    if name == "cusum": return CUSUMDetector(baseline, cusum_k, cusum_h)
    raise ValueError(f"unknown detector: {name}")
