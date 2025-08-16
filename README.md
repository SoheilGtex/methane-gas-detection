<h1 align="center">🧪 Methane Gas Detection (Python)</h1>
<p align="center">Real-time methane detection using MQ-4/MQ-135 with Python. Includes serial & simulator modes, calibration, smoothing, logging, and optional PPM estimation.</p>

<div align="center">
  <img src="https://img.shields.io/badge/Sensors-MQ4%20%7C%20MQ135-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/Language-Python-3776AB?style=flat-square"/>
  <img src="https://img.shields.io/badge/Modes-Serial%20%7C%20Simulator-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/Features-Calibration%20%7C%20Smoothing%20%7C%20Alerts%20%7C%20Logging-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square"/>
</div>

---

## ✨ Features
- **Serial mode** (MQ-4/MQ-135 via Arduino/ESP32 → USB/COM)
- **Simulator mode** (بدون سخت‌افزار)
- **Auto-calibration** (baseline μ/σ) + **hysteresis** برای کاهش نوسان
- **Smoothing** (EMA / Moving Average)
- **Logging** به CSV + **Static Plot** خروجی
- **Optional PPM estimation** از نسبت Rs/R0 (تقریبی)
- **Configurable** از طریق `config.yaml`

> ⚠️ **Disclaimer:** مدل PPM تقریبی است و برای استفاده‌های ایمنی صنعتی کافی نیست. برای کاربردهای ایمنی از تجهیزات استاندارد استفاده کنید.

---

## 🚀 Quickstart

```bash
# 1) Install
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt

# 2) Run (Simulator)
python -m src.main --mode sim --duration 60 --save data/sample_sim.csv --plot

# 3) Run (Serial)
# Example: --port COM5 (Windows) or /dev/ttyUSB0 (Linux)
python -m src.main --mode serial --port COM5 --baud 9600 --duration 120 --save data/run.csv --plot
