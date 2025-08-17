import csv
from pathlib import Path
from .utils import now_iso

class CsvLogger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("w", newline="", encoding="utf-8")
        self._wr = csv.writer(self._fh)
        self._wr.writerow(["timestamp","raw","smooth","alert","ppm"])

    def write(self, raw, smooth, alert, ppm=None):
        self._wr.writerow([now_iso(), raw, smooth, int(alert), "" if ppm is None else ppm])

    def close(self):
        try:
            self._fh.close()
        except Exception:
            pass
