<h1 align="center">🧪 Methane Gas Detection (Python)</h1>
<p align="center">
  Real-time methane detection using MQ-4/MQ-135 in Python. Includes Serial & Simulator modes, calibration, smoothing, hysteresis-based alerting, CSV logging, and optional PPM estimation.
</p>

<div align="center">
  <img src="https://img.shields.io/badge/Sensors-MQ4%20%7C%20MQ135-blue?style=flat-square"/>
  <img src="https://img.shields.io/badge/Language-Python-3776AB?style=flat-square"/>
  <img src="https://img.shields.io/badge/Modes-Serial%20%7C%20Simulator-yellow?style=flat-square"/>
  <img src="https://img.shields.io/badge/Features-Calibration%20%7C%20Smoothing%20%7C%20Hysteresis%20%7C%20Logging-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square"/>
</div>

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Quickstart](#quickstart)
- [Hardware (Optional)](#hardware-optional)
- [Configuration](#configuration)
- [Detection Logic](#detection-logic)
- [CLI Usage](#cli-usage)
- [Outputs](#outputs)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [License](#license)
- [Author](#author)

---

## Overview
This project provides a clean, reproducible template for **real-time methane detection** using low-cost gas sensors (MQ-4 / MQ-135). It supports both **Serial** (Arduino/ESP32) and **Simulator** modes, enabling quick experimentation without hardware. A simple detection pipeline uses **auto-calibration**, **smoothing (EMA/MA)**, and **hysteresis** to reduce noise and flicker.

> ⚠️ **Disclaimer:** PPM estimation here is **approximate** and **not suitable** for industrial safety. For safety-critical use, employ certified equipment.

---

## Features
- **Serial & Simulator** modes (switchable)
- **Auto-calibration** (mean/σ) over a warm-up window
- **Smoothing:** Exponential Moving Average (EMA) or Moving Average (MA)
- **Hysteresis-based alerting** to avoid flapping
- **CSV logging** (timestamp, raw, smooth, alert, ppm)
- **Static plot** generation (PNG) for quick analysis
- **Configurable** via `config.yaml`
- **Optional PPM estimation** from Rs/R0 curve (very rough)

---

## Tech Stack

| Category       | Technologies                          |
|----------------|---------------------------------------|
| Language       | Python                                 |
| I/O            | `pyserial` (Serial), simulator source  |
| Data           | `numpy`, `pandas`                      |
| Viz            | `matplotlib`                           |
| Config         | `pyyaml`                               |

---

## Repository Structure
