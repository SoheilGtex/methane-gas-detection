import yaml
from pathlib import Path

DEFAULT = {
    "mode": "sim",
    "serial": {"port": "COM5", "baud": 9600},
    "sampling_hz": 5,
    "calibration_seconds": 12,
    "smooth": {"type": "ema", "ema_alpha": 0.2, "ma_window": 8},
    "threshold": {"k_sigma": 3.0, "hysteresis": 0.5},
    "ppm": {"enabled": False, "rs_r0": 1.0},
    "output": {"save_csv": "data/sample_sim.csv", "make_plot": True, "plot_path": "data/plot.png"},
}

def load_config(path="config.yaml"):
    p = Path(path)
    if not p.exists():
        return DEFAULT
    with p.open("r", encoding="utf-8") as f:
        user = yaml.safe_load(f) or {}
    # shallow merge
    cfg = DEFAULT.copy()
    for k, v in user.items():
        if isinstance(v, dict) and k in cfg:
            sub = cfg[k].copy()
            sub.update(v)
            cfg[k] = sub
        else:
            cfg[k] = v
    return cfg
