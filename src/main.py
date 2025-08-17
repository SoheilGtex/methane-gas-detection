import argparse, sys, time
from statistics import mean
from .config import load_config
from .serial_reader import SerialReader
from .sim_source import sim_stream
from .filters import MovingAverage, EMA
from .detector import GasDetector
from .ppm_models import ppm_from_rs_ratio
from .logger import CsvLogger
from .viz import plot_csv

def parse_args():
    p = argparse.ArgumentParser(description="Methane detection (serial/simulator)")
    p.add_argument("--mode", choices=["sim","serial"], help="Override config mode")
    p.add_argument("--port", help="Serial port (e.g., COM5 or /dev/ttyUSB0)")
    p.add_argument("--baud", type=int, help="Serial baudrate (default from config)")
    p.add_argument("--duration", type=int, default=60, help="Seconds to run")
    p.add_argument("--save", help="CSV output path; overrides config")
    p.add_argument("--plot", action="store_true", help="Generate plot after run")
    return p.parse_args()

def get_filter(cfg):
    st = cfg["smooth"]["type"]
    if st == "ma":
        return MovingAverage(cfg["smooth"]["ma_window"])
    return EMA(cfg["smooth"]["ema_alpha"])

def main():
    args = parse_args()
    cfg = load_config()

    if args.mode: cfg["mode"] = args.mode
    if args.port: cfg["serial"]["port"] = args.port
    if args.baud: cfg["serial"]["baud"] = args.baud
    if args.save: cfg["output"]["save_csv"] = args.save
    if args.plot: cfg["output"]["make_plot"] = True

    hz = int(cfg["sampling_hz"])
    dt = 1.0 / max(1, hz)
    calib_secs = int(cfg["calibration_seconds"])
    out_csv = cfg["output"]["save_csv"]

    # Source
    reader = None
    if cfg["mode"] == "serial":
        reader = SerialReader(cfg["serial"]["port"], cfg["serial"]["baud"])
        try:
            reader.open()
            print(f"[i] Serial opened on {cfg['serial']['port']} @ {cfg['serial']['baud']}")
        except Exception as e:
            print(f"[!] Serial open failed: {e}")
            sys.exit(1)
        source = lambda: reader.read_value()
    else:
        gen = sim_stream(hz=hz)
        source = lambda: next(gen)

    # Calibration
    print(f"[i] Calibrating for {calib_secs}s ...")
    calib = []
    t0 = time.time()
    while time.time() - t0 < calib_secs:
        v = source()
        if v is not None:
            calib.append(float(v))
        time.sleep(dt)
    if len(calib) < 5:
        print("[!] Not enough samples for calibration.")
        sys.exit(1)

    filt = get_filter(cfg)
    det = GasDetector(k_sigma=cfg["threshold"]["k_sigma"],
                      hysteresis=cfg["threshold"]["hysteresis"])
    det.calibrate(calib)
    print(f"[i] μ={det.mu:.2f} σ={det.sigma:.2f} thr={det.threshold:.2f}")

    log = CsvLogger(out_csv)
    print(f"[i] Logging → {out_csv}")

    # Run
    run_until = time.time() + int(args.duration)
    try:
        while time.time() < run_until:
            v = source()
            if v is None:
                time.sleep(dt); continue
            smooth = filt.update(float(v))

            alert = det.update(smooth)

            ppm = None
            # Optional PPM — requires correct Rs/R0 pipeline (not included by default)
            if cfg["ppm"]["enabled"]:
                ppm = ppm_from_rs_ratio(cfg["ppm"]["rs_r0"])

            log.write(raw=v, smooth=smooth, alert=alert, ppm=ppm)

            # status line
            print(f"\rraw={v:4d}  smooth={smooth:7.2f}  alert={'YES' if alert else 'no '}", end="")
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    finally:
        log.close()
        if reader: reader.close()
        print("\n[i] Done.")

    # Plot
    if cfg["output"]["make_plot"]:
        try:
            plot_csv(out_csv, cfg["output"]["plot_path"])
            print(f"[i] Plot saved → {cfg['output']['plot_path']}")
        except Exception as e:
            print(f"[!] Plot failed: {e}")

if __name__ == "__main__":
    main()
