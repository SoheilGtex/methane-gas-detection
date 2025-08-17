import time
import serial

class SerialReader:
    def __init__(self, port, baud=9600, timeout=1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._ser = None

    def open(self):
        self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        time.sleep(1.5)  # allow MCU reset

    def close(self):
        try:
            if self._ser and self._ser.is_open:
                self._ser.close()
        except Exception:
            pass

    def read_value(self):
        """
        Expect one line per sample, e.g. '315\\n'
        Returns int (0..1023) or None
        """
        if not self._ser:
            return None
        line = self._ser.readline().decode(errors="ignore").strip()
        if not line:
            return None
        try:
            return int(line)
        except ValueError:
            return None
