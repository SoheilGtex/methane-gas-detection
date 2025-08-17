from collections import deque

class MovingAverage:
    def __init__(self, window=8):
        self.window = max(1, int(window))
        self.buf = deque(maxlen=self.window)
        self.sum = 0.0

    def update(self, x):
        if len(self.buf) == self.window:
            self.sum -= self.buf[0]
        self.buf.append(x)
        self.sum += x
        return self.sum / len(self.buf)

class EMA:
    def __init__(self, alpha=0.2):
        self.alpha = float(alpha)
        self.y = None

    def update(self, x):
        if self.y is None:
            self.y = float(x)
        else:
            self.y = self.alpha*float(x) + (1-self.alpha)*self.y
        return self.y
