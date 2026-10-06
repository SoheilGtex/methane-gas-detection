# Technical Report: Final Experimental Integrity Pass

**Status:** unpublished technical report; not a paper or peer-reviewed publication.

## Abstract

This final integrity pass hardens a synthetic sensor-monitoring benchmark against four classes of validity failure: vacuous drift scenarios, duplicate alarm onset misclassification, inconsistent preprocessing signal spaces, and artifacts generated from dirty source code. The implementation now requires explicit non-zero drift, distinguishes matched/duplicate/false alarm onsets, uses one preprocessing filter across baseline and detection, persists complete synthetic ground truth including missing rows, and provides a committed smoke command. Outputs are generated from a clean source revision and record that revision with `git_dirty=false`.

## Exact semantic fixes

### Non-vacuous drift

`Scenario.DRIFT` now requires `drift_per_sample != 0`. The smoke command explicitly uses `0.25` units per synthetic sample. This value is serialized into each drift experiment's simulation configuration. Drift is a nuisance condition, not a leak event; its `is_leak` labels remain false.

### Detector trigger classification

A ground-truth event is a maximal **half-open interval** `[start, end)` of contiguous leak labels. Alarm state is Boolean at each sample, while detector triggers are explicit detector signals preserved by the pipeline. Threshold, Z-score, and EWMA detectors trigger when their persistent hysteresis state enters active. Signal-and-reset CUSUM triggers on every threshold crossing, including consecutive crossings; it is not reduced to `False → True` transitions in the Boolean alarm sequence.

Each detector trigger is assigned exactly one class:

1. matched event onset: first trigger inside a previously undetected event;
2. duplicate event onset: later trigger inside an already detected event;
3. false-alarm onset: trigger outside every leak interval.

Event matching, detection delay, and onset classification use these explicit detector triggers, not reconstructed state transitions. Thus duplicate CUSUM signals remain visible in `duplicate_event_onsets` and are not incorrectly counted as false alarms. A late trigger after `event_end` is a false alarm and cannot detect the ended event.

### CUSUM

CUSUM uses signal-and-reset semantics. It accumulates positive standardized changes with reference value `k`; on crossing `h`, it emits an alarm for that sample and resets. Because global hysteresis does not affect this behavior, CUSUM effective metadata contains only `cusum_k` and `cusum_h`.

CUSUM therefore exposes one-sample signal-and-reset alarm pulses, whereas Threshold, Z-score, and EWMA expose persistent alarm states. Sample/state metrics should not be interpreted as perfectly equivalent alarm-duration semantics across all detector families.

### Consistent signal space

When preprocessing is enabled, one configured EMA instance processes the warm-up samples first. Baseline mean and standard deviation are estimated from those filtered values, and the same filter state continues into detection. When disabled, both baseline and detector operate on raw values. Missing warm-up values are skipped, and at least two finite processed baseline values are required.

The EWMA detector has a distinct recursive statistic. If common preprocessing is enabled, the detector receives the already smoothed stream and then applies `detector_ewma_alpha`: this is an intentional two-stage smoothing composition. The two parameters are named separately in configuration and metadata.

### Persistence and source metadata

SQLite preserves `sample_index`, `simulated_time`, nullable raw and filtered values, `is_leak`, `artifact_type`, `source`, and `run_id`. Missing simulator samples remain rows with null values and `artifact_type="missing"`. Simulator rows preserve leak/artifact labels. Serial rows use `source="serial"`, null simulation seed/scenario/configuration, and unknown hardware ground truth.

## Baseline window semantics

`baseline_window_samples` names the fixed initial positional warm-up window. Missing values inside it are skipped, and at least two finite processed values are required. The legacy input key `min_baseline_samples` is accepted as an alias; serialized metadata uses the corrected name.

## Metric definitions

For labels `L_t` and alarm state `A_t`:

- `alarm_active_samples = Σ A_t`.
- detector triggers are explicit detector signals preserved by the pipeline; stateful detectors trigger only on entry to alarm, while signal-and-reset CUSUM triggers on every crossing;
- events are half-open intervals `[s_j,e_j)` from contiguous `L_t=True`;
- an event is detected iff its first matched detector trigger satisfies `s_j <= trigger < e_j`;
- duplicate event onsets are additional detector triggers inside a matched event;
- false-alarm episodes are detector triggers outside all event intervals;
- `TP = Σ(L_t and A_t)`, `FP = Σ(not L_t and A_t)`, `TN = Σ(not L_t and not A_t)`, `FN = Σ(L_t and not A_t)`;
- `sample_precision = TP/(TP+FP)`;
- `sample_recall = TP/(TP+FN)`;
- `sample_f1 = 2PR/(P+R)`;
- `false_positive_sample_rate = FP/(FP+TN)`;
- `time_in_alarm_fraction = ΣA_t/N`.

Undefined ratios use zero denominators conservatively as zero. Event-level and sample-level metrics are never mixed.

## Reproducibility workflow

The source/test/configuration changes were committed first as:

```text
CODE_COMMIT_2_2 = 8f29627f1a6359ee8735af263f07814df2b37fd0
```

The worktree was clean. From that clean commit, the following were executed:

```bash
pytest
ruff check .
methane-monitor --config config.yaml benchmark --output /tmp/benchmark-code-commit.json
methane-monitor --config config.yaml smoke \
  --seeds 1 7 19 42 101 \
  --scenarios stable sudden_leak gradual_leak drift \
  --drift-rate 0.25 \
  --output /tmp/smoke-code-commit.json
```

Both generated artifacts recorded the CODE_COMMIT and `git_dirty=false`. The artifacts and documentation were then copied into the repository and committed separately. The final artifact commit is reported in the completion response.

## Default benchmark result

The clean-code default benchmark produced:

| Detector | Event detection rate | Mean delay | False-alarm episodes | Duplicate onsets | False-positive sample rate | Time in alarm |
|---|---:|---:|---:|---:|---:|---:|
| Threshold | 1.0000 | 1.0 | 0 | 0 | 0.0227 | 0.2800 |
| Z-score | 1.0000 | 0.0 | 0 | 0 | 0.0591 | 0.3100 |
| EWMA | 1.0000 | 1.0 | 0 | 0 | 0.0864 | 0.3267 |
| CUSUM | 1.0000 | 0.0 | 12 | 79 | 0.0545 | 0.3067 |

These values describe one synthetic configuration. They are not real-world methane detection performance claims.

## Smoke matrix

The committed smoke command generated 20 seed/scenario combinations: seeds `1, 7, 19, 42, 101` across `stable`, `sudden_leak`, `gradual_leak`, and `drift`. The drift value was explicitly `0.25`. The raw runs and per-detector summaries are in `results/multi_seed_smoke.json`.

For stable and drift, event detection rate is not informative because there are no leak events; false-alarm episodes, false-positive sample rate, duplicate onsets, and time in alarm are the relevant diagnostics. Five seeds are a smoke check, not evidence of general robustness.

## Validation status

- **IMPLEMENTED AND TESTED:** drift validation, onset classes, event/sample metric separation, same-space preprocessing, effective CUSUM metadata, ground-truth persistence, serial metadata separation, smoke command, clean-code artifact workflow, SQLite/API behavior, 22 focused tests, and Ruff.
- **IMPLEMENTED BUT UNVERIFIED:** serial execution on physical hardware; Dockerfile; remote GitHub Actions.
- **NOT IMPLEMENTED:** physical gas calibration, real sensor dataset, PostgreSQL, frontend, visualization, ML, cloud deployment, and certified safety evaluation.

Docker remains **NOT RUN** because the Docker CLI is unavailable. Remote CI remains **UNVERIFIED** because no remote workflow run was observed.
