from __future__ import annotations

from statistics import median


def _intervals(labels: list[bool]) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    start = None
    for index, active in enumerate(labels + [False]):
        if active and start is None: start = index
        elif not active and start is not None: intervals.append((start, index)); start = None
    return intervals


def evaluate(is_leak: list[bool], alarm_state: list[bool], trigger_mask: list[bool] | None = None, *, sample_period: float = 1.0) -> dict[str, float | int | None]:
    if len(is_leak) != len(alarm_state): raise ValueError("is_leak and alarm_state must have equal length")
    triggers = trigger_mask if trigger_mask is not None else [active and (i == 0 or not alarm_state[i - 1]) for i, active in enumerate(alarm_state)]
    if len(triggers) != len(is_leak): raise ValueError("trigger_mask must have equal length")
    leak_intervals = _intervals(is_leak)
    matched_onsets: list[int] = []
    matched_event_indices: set[int] = set()
    duplicate_onsets: list[int] = []
    false_onsets: list[int] = []
    delays: list[float] = []
    for onset in (i for i, trigger in enumerate(triggers) if trigger):
        event_index = next((index for index, (start, end) in enumerate(leak_intervals) if start <= onset < end), None)
        if event_index is None: false_onsets.append(onset)
        elif event_index in matched_event_indices: duplicate_onsets.append(onset)
        else:
            start, _ = leak_intervals[event_index]
            matched_event_indices.add(event_index); matched_onsets.append(onset); delays.append((onset - start) * sample_period)
    tp = sum(leak and alarm for leak, alarm in zip(is_leak, alarm_state))
    fp = sum(not leak and alarm for leak, alarm in zip(is_leak, alarm_state))
    tn = sum(not leak and not alarm for leak, alarm in zip(is_leak, alarm_state))
    fn = sum(leak and not alarm for leak, alarm in zip(is_leak, alarm_state))
    sample_precision = tp / (tp + fp) if tp + fp else 0.0
    sample_recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "total_events": len(leak_intervals), "detected_events": len(matched_onsets), "missed_events": len(leak_intervals) - len(matched_onsets),
        "event_detection_rate": len(matched_onsets) / len(leak_intervals) if leak_intervals else 0.0,
        "mean_detection_delay": sum(delays) / len(delays) if delays else None, "median_detection_delay": median(delays) if delays else None,
        "detector_triggers": sum(triggers), "matched_event_onsets": len(matched_onsets), "duplicate_event_onsets": len(duplicate_onsets),
        "false_alarm_episodes": len(false_onsets), "alarm_active_samples": sum(alarm_state), "false_positive_samples": fp,
        "true_positive_samples": tp, "true_negative_samples": tn, "false_negative_samples": fn,
        "sample_precision": sample_precision, "sample_recall": sample_recall,
        "sample_f1": 2 * sample_precision * sample_recall / (sample_precision + sample_recall) if sample_precision + sample_recall else 0.0,
        "false_positive_sample_rate": fp / max(1, fp + tn), "time_in_alarm_fraction": sum(alarm_state) / max(1, len(alarm_state)),
    }
