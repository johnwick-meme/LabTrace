"""
core/calculations.py — Deterministic Ohm's law calculations.

Owned by: Programmer 2.

All mathematical results are computed here in Python.
No values are accepted from the language model.

Public API (agreed function contract):
    calculate_resistance(voltage, current) -> float
    compare_readings(readings) -> dict
    calculate_experiment(payload) -> dict   ← wrapper required by app.py adapter
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _validate_number(value: Any, field: str, allow_zero: bool = True) -> float:
    """
    Convert *value* to float and validate it.

    Raises
    ------
    TypeError  if the value cannot be converted to a number.
    ValueError if the value is negative, or zero when allow_zero is False.
    """
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"{field} must be a number, got {type(value).__name__!r}: {value!r}"
        ) from exc

    if parsed < 0:
        raise ValueError(f"{field} cannot be negative (got {parsed}).")
    if not allow_zero and parsed == 0.0:
        raise ValueError(f"{field} cannot be zero.")
    return parsed


# ---------------------------------------------------------------------------
# Core calculation functions
# ---------------------------------------------------------------------------

def calculate_resistance(voltage: Any, current: Any) -> float:
    """
    Calculate resistance using Ohm's law: R = V / I.

    Parameters
    ----------
    voltage : numeric
        Potential difference in volts (V >= 0).
    current : numeric
        Current in amperes (I > 0).

    Returns
    -------
    float
        Resistance in ohms.

    Raises
    ------
    TypeError   if either argument is not a number.
    ValueError  if voltage is negative, or current is zero or negative.

    Examples
    --------
    >>> calculate_resistance(10.0, 2.0)
    5.0
    >>> calculate_resistance(0.0, 1.0)
    0.0
    """
    v = _validate_number(voltage, "voltage", allow_zero=True)
    i = _validate_number(current, "current", allow_zero=False)
    return v / i


def compare_readings(readings: list[dict]) -> dict:
    """
    Analyse a list of voltage/current readings and identify discrepancies.

    Each reading must contain ``voltage_v`` and ``current_a`` keys.

    A reading is flagged as a discrepancy when its calculated resistance
    differs from the baseline mean (first three valid readings) by more
    than DISCREPANCY_THRESHOLD (20 %).

    Parameters
    ----------
    readings : list of dict
        Each dict must have ``voltage_v`` and ``current_a``.

    Returns
    -------
    dict with keys:
        rows          : list[dict]  — per-trial results including resistance
        valid_count   : int         — number of readings with calculable R
        baseline_mean_ohm : float | None
        discrepancies : list[dict]  — flagged readings with reason
        summary       : str

    Raises
    ------
    TypeError  if readings is not a list.
    ValueError if readings is empty.
    """
    if not isinstance(readings, list):
        raise TypeError(f"readings must be a list, got {type(readings).__name__!r}.")
    if not readings:
        raise ValueError("readings list must not be empty.")

    DISCREPANCY_THRESHOLD = 0.20  # 20 % relative deviation from baseline mean

    rows: list[dict] = []
    errors: list[str] = []

    for idx, reading in enumerate(readings, start=1):
        if not isinstance(reading, dict):
            errors.append(f"Trial {idx}: expected a dict, got {type(reading).__name__!r}.")
            rows.append({
                "trial": idx,
                "voltage_v": None,
                "current_a": None,
                "resistance_ohm": None,
                "status": "skipped — not a dict",
                "original": reading,
            })
            continue

        raw_v = reading.get("voltage_v", reading.get("voltage", reading.get("V")))
        raw_i = reading.get("current_a", reading.get("current", reading.get("I")))

        try:
            v = _validate_number(raw_v, f"Trial {idx} voltage", allow_zero=True)
            i = _validate_number(raw_i, f"Trial {idx} current", allow_zero=False)
            r = v / i
            status = "ok"
        except (TypeError, ValueError) as exc:
            v = raw_v
            i = raw_i
            r = None
            status = str(exc)

        rows.append({
            "trial": idx,
            "voltage_v": v,
            "current_a": i,
            "resistance_ohm": r,
            "status": status,
        })

    # Baseline: mean of the first three valid resistance values
    valid_resistances = [row["resistance_ohm"] for row in rows if row["resistance_ohm"] is not None]
    baseline_sample = valid_resistances[:3]
    baseline_mean: float | None = (
        sum(baseline_sample) / len(baseline_sample) if baseline_sample else None
    )
    valid_count = len(valid_resistances)

    # Identify discrepancies
    discrepancies: list[dict] = []
    if baseline_mean is not None:
        for row in rows:
            if row["resistance_ohm"] is None:
                continue
            r = row["resistance_ohm"]
            deviation = abs(r - baseline_mean) / max(abs(baseline_mean), 1e-9)
            if deviation > DISCREPANCY_THRESHOLD:
                discrepancies.append({
                    "trial": row["trial"],
                    "resistance_ohm": r,
                    "baseline_mean_ohm": round(baseline_mean, 4),
                    "deviation_pct": round(deviation * 100, 2),
                    "reason": (
                        f"Trial {row['trial']} resistance {r:.4f} Ω deviates "
                        f"{deviation * 100:.1f} % from the baseline mean "
                        f"{baseline_mean:.4f} Ω (threshold {DISCREPANCY_THRESHOLD * 100:.0f} %)."
                    ),
                })

    # Summary
    if not discrepancies:
        summary = (
            f"All {valid_count} calculable reading(s) are consistent with "
            f"the baseline mean of {baseline_mean:.4f} Ohm."
            if baseline_mean is not None
            else "No valid readings to compare."
        )
    else:
        summary = (
            f"{len(discrepancies)} of {valid_count} reading(s) deviate from "
            f"the baseline mean of {baseline_mean:.4f} Ohm by more than "
            f"{DISCREPANCY_THRESHOLD * 100:.0f} %."
        )

    # Median calculation for compatibility with P1's expectations
    valid_sorted = sorted(valid_resistances)
    if not valid_sorted:
        median_r = None
    elif len(valid_sorted) % 2 == 1:
        median_r = valid_sorted[len(valid_sorted) // 2]
    else:
        mid = len(valid_sorted) // 2
        median_r = (valid_sorted[mid - 1] + valid_sorted[mid]) / 2

    # Map discrepancies to P1 anomalies format with index and reason
    anomalies = []
    for d in discrepancies:
        anomalies.append({
            "index": d["trial"] - 1,
            "reading": readings[d["trial"] - 1] if d["trial"] - 1 < len(readings) else {},
            "resistance": d["resistance_ohm"],
            "expected": median_r,
            "deviation_pct": d.get("deviation_pct", 0.0),
            "reason": d["reason"],
        })

    result = {
        "rows": rows,
        "valid_count": valid_count,
        "baseline_mean_ohm": round(baseline_mean, 6) if baseline_mean is not None else None,
        "discrepancies": discrepancies,
        "summary": summary,
        # P1 compatibility fields
        "median_resistance": median_r,
        "resistances": [r["resistance_ohm"] for r in rows],
        "anomalies": anomalies,
        "consistent_count": valid_count - len(discrepancies),
    }
    if errors:
        result["parse_errors"] = errors

    return result


# ---------------------------------------------------------------------------
# Higher-level wrapper (required by app.py's run_calculation_adapter)
# ---------------------------------------------------------------------------

def calculate_experiment(payload: dict | None = None, **kwargs) -> dict:
    """
    Wrapper called by the app.py integration adapter.

    Accepts either a single dict payload or keyword arguments.

    Expected keys in payload (or kwargs):
        readings  : list[dict]  — required; list of voltage/current dicts
        title     : str         — optional experiment label

    Returns
    -------
    dict with the same shape as compare_readings() plus:
        title         : str
        mode          : str
        calculations  : dict  (alias for the full result, for adapter compatibility)

    Raises
    ------
    ValueError if no readings can be found in the payload.
    """
    # Merge payload dict with any extra kwargs
    combined: dict = {}
    if isinstance(payload, dict):
        combined.update(payload)
    combined.update(kwargs)

    # Accept readings under several plausible keys
    readings = (
        combined.get("readings")
        or combined.get("measurements")
        or combined.get("trials")
    )

    if not isinstance(readings, list) or not readings:
        raise ValueError(
            "calculate_experiment: payload must contain a non-empty 'readings' list. "
            f"Keys received: {list(combined.keys())}"
        )

    title = combined.get("title", "Untitled experiment")
    result = compare_readings(readings)
    result["title"] = title
    result["mode"] = "deterministic Python calculation (not language model output)"
    # Alias so the adapter can also find it under 'calculations'
    result["calculations"] = {k: v for k, v in result.items() if k != "calculations"}
    return result
