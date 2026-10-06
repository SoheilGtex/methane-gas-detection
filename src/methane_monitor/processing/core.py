from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class Baseline:
    mean: float
    sigma: float
    count: int


def estimate_baseline(values: list[float]) -> Baseline:
    if len(values) < 2:
        raise ValueError("at least two finite samples are required for baseline estimation")
    if any(v != v or v in (float("inf"), float("-inf")) for v in values):
        raise ValueError("baseline samples must be finite")
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return Baseline(mean, max(sqrt(variance), 1e-12), len(values))


class ExponentialMovingAverage:
    def __init__(self, alpha: float):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha, self.value = alpha, None

    def update(self, value: float) -> float:
        self.value = float(value) if self.value is None else self.alpha * value + (1 - self.alpha) * self.value
        return self.value


class MovingAverage:
    def __init__(self, window: int):
        if window < 1:
            raise ValueError("window must be positive")
        self.values = deque(maxlen=window)

    def update(self, value: float) -> float:
        self.values.append(float(value))
        return sum(self.values) / len(self.values)
