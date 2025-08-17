import math, random, time

def sim_stream(hz=5, spike_every=20, base=320, noise=6, spike_amp=120):
    """
    Yields simulated ADC-like integers with occasional spikes.
    """
    dt = 1.0 / max(1, hz)
    t = 0
    k = 0
    while True:
        # base + low-frequency drift + noise
        drift = 8 * math.sin(t/35.0) + 5 * math.sin(t/15.0)
        val = base + drift + random.gauss(0, noise)
        # occasional spike
        if k % max(5, spike_every) == 0 and random.random() < 0.12:
            val += spike_amp * (0.7 + 0.6*random.random())
        yield int(max(0, min(1023, round(val))))
        k += 1
        t += 1
        time.sleep(dt)
