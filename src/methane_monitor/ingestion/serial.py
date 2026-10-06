from __future__ import annotations

from collections.abc import Iterator

from methane_monitor.ingestion.simulator import SimulatedSample
from methane_monitor.models import ArtifactType


class SerialSource:
    def __init__(self, port: str, baud: int = 9600, timeout: float = 1.0, sample_period: float = 1.0):
        self.port, self.baud, self.timeout, self.sample_period = port, baud, timeout, sample_period

    def __iter__(self) -> Iterator[SimulatedSample]:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("Serial mode requires the optional 'serial' dependency") from exc
        with serial.Serial(self.port, self.baud, timeout=self.timeout) as connection:
            index = 0
            while True:
                line = connection.readline().decode(errors="ignore").strip()
                value = None
                if line:
                    try: value = float(line)
                    except ValueError: pass
                yield SimulatedSample(index, index * self.sample_period, value, False, ArtifactType.MISSING if value is None else ArtifactType.NONE)
                index += 1
