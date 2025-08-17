import statistics

class GasDetector:
    def __init__(self, k_sigma=3.0, hysteresis=0.5):
        self.k = float(k_sigma)
        self.hyst = float(hysteresis)
        self.mu = None
        self.sigma = None
        self.threshold = None
        self.alert = False

    def calibrate(self, samples):
        if not samples:
            raise ValueError("No samples to calibrate.")
        self.mu = statistics.mean(samples)
        self.sigma = statistics.pstdev(samples) or 1.0
        self.threshold = self.mu + self.k * self.sigma

    def update(self, value):
        if self.threshold is None:
            return False
        if not self.alert and value > self.threshold:
            self.alert = True
        elif self.alert and value < (self.threshold - self.hyst*self.sigma):
            self.alert = False
        return self.alert
