"""
core/calculations.py — STUB (Programmer 2's responsibility)

These are placeholder implementations matching the agreed function
signatures. They will be replaced by Programmer 2's real code.

Agreed signatures:
    calculate_resistance(voltage, current) -> float
    compare_readings(readings) -> dict
"""


def calculate_resistance(voltage, current):
    """
    Calculate resistance using Ohm's law: R = V / I.

    Parameters:
        voltage (float): Voltage in volts.
        current (float): Current in amperes.  Must not be zero.

    Returns:
        float: Resistance in ohms.

    Raises:
        ZeroDivisionError: If current is zero.
        TypeError: If inputs are not numbers.
    """
    if not isinstance(voltage, (int, float)):
        raise TypeError(f"voltage must be a number, got {type(voltage).__name__}")
    if not isinstance(current, (int, float)):
        raise TypeError(f"current must be a number, got {type(current).__name__}")
    if current == 0:
        raise ZeroDivisionError("Cannot calculate resistance: current is zero.")
    return voltage / current


def compare_readings(readings):
    """
    Compare a list of readings and flag anomalies.

    Each reading is a dict: {"voltage": float, "current": float}

    Returns a dict with:
        "resistances": list of calculated resistances (None if current was zero),
        "median_resistance": the median resistance of valid readings,
        "anomalies": list of dicts describing anomalous readings,
        "consistent_count": number of readings close to the median.

    A reading is considered anomalous if its resistance differs from the
    median by more than 10%.
    """
    if not readings:
        return {
            "resistances": [],
            "median_resistance": None,
            "anomalies": [],
            "consistent_count": 0,
        }

    # Calculate resistance for each reading
    resistances = []
    for r in readings:
        v = r.get("voltage")
        i = r.get("current")
        if i is not None and i != 0 and isinstance(v, (int, float)) and isinstance(i, (int, float)):
            resistances.append(v / i)
        else:
            resistances.append(None)

    # Find the median of valid resistances
    valid = sorted([r for r in resistances if r is not None])
    if not valid:
        return {
            "resistances": resistances,
            "median_resistance": None,
            "anomalies": [],
            "consistent_count": 0,
        }

    mid = len(valid) // 2
    if len(valid) % 2 == 1:
        median_r = valid[mid]
    else:
        median_r = (valid[mid - 1] + valid[mid]) / 2

    # Flag anomalies (>10% deviation from median)
    THRESHOLD = 0.10
    anomalies = []
    consistent_count = 0
    for index, res in enumerate(resistances):
        if res is None:
            anomalies.append({
                "index": index,
                "reading": readings[index],
                "resistance": None,
                "reason": "Could not calculate resistance (zero or missing current).",
            })
        elif abs(res - median_r) / median_r > THRESHOLD:
            anomalies.append({
                "index": index,
                "reading": readings[index],
                "resistance": res,
                "expected": median_r,
                "deviation_pct": round(abs(res - median_r) / median_r * 100, 1),
                "reason": (
                    f"Resistance ({res:.2f} Ω) deviates "
                    f"{abs(res - median_r) / median_r * 100:.1f}% "
                    f"from median ({median_r:.2f} Ω)."
                ),
            })
        else:
            consistent_count += 1

    return {
        "resistances": resistances,
        "median_resistance": median_r,
        "anomalies": anomalies,
        "consistent_count": consistent_count,
    }
