import math
from numbers import Real


def _validate_number(value, field_name):
    """Check that an input is a real, finite number."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a number.")

    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")

    return float(value)


def calculate_resistance(voltage, current):
    """Calculate resistance using Ohm's law: R = V / I."""
    voltage = _validate_number(voltage, "Voltage")
    current = _validate_number(current, "Current")

    if current == 0:
        raise ValueError("Current cannot be zero.")

    resistance = voltage / current

    return {
        "voltage_v": voltage,
        "current_a": current,
        "resistance_ohm": resistance,
    }


def compare_readings(readings, tolerance=0.05):
    """
    Compare valid resistance readings against their median.

    tolerance=0.05 means a 5% deviation is allowed.
    Readings outside the tolerance are flagged, never corrected.
    """
    if not isinstance(readings, list) or not readings:
        raise ValueError("Readings must be a non-empty list.")

    tolerance = _validate_number(tolerance, "Tolerance")

    if not 0 <= tolerance < 1:
        raise ValueError("Tolerance must be between 0 and 1.")

    results = []
    valid_resistances = []

    for index, reading in enumerate(readings):
        reading_id = f"R{index + 1}"

        try:
            if not isinstance(reading, dict):
                raise ValueError("Reading must be a dictionary.")

            reading_id = reading.get("reading_id", reading_id)

            if "voltage_v" not in reading or "current_a" not in reading:
                raise ValueError("Voltage or current is missing.")

            calculation = calculate_resistance(
                reading["voltage_v"],
                reading["current_a"],
            )

            result = {
                "reading_id": reading_id,
                "valid": True,
                "calculation": calculation,
                "anomaly": False,
                "deviation_fraction": None,
                "message": "Awaiting comparison.",
            }

            valid_resistances.append(
                (len(results), calculation["resistance_ohm"])
            )

        except (ValueError, TypeError, OverflowError) as error:
            result = {
                "reading_id": reading_id,
                "valid": False,
                "calculation": None,
                "anomaly": False,
                "deviation_fraction": None,
                "message": str(error),
            }

        results.append(result)

    if not valid_resistances:
        return {
            "reference_resistance_ohm": None,
            "tolerance_fraction": tolerance,
            "readings": results,
            "anomalies": [],
            "message": "No valid resistance readings to compare.",
        }

    # Calculate the median without modifying any original reading.
    values = sorted(value for _, value in valid_resistances)
    middle = len(values) // 2

    if len(values) % 2:
        reference = values[middle]
    else:
        reference = (values[middle - 1] + values[middle]) / 2

    anomalies = []

    for index, resistance in valid_resistances:
        result = results[index]

        if reference == 0:
            # Relative deviation is undefined for a zero reference.
            # Flag differing values without inventing a percentage.
            deviation = None
            is_anomaly = resistance != 0
        else:
            deviation = abs(resistance - reference) / abs(reference)
            is_anomaly = deviation > tolerance

        result["deviation_fraction"] = deviation
        result["anomaly"] = is_anomaly

        if is_anomaly:
            result["message"] = (
                "Resistance differs from the reference; investigate."
            )
            anomalies.append(result["reading_id"])
        else:
            result["message"] = "Within the configured tolerance."

    return {
        "reference_resistance_ohm": reference,
        "tolerance_fraction": tolerance,
        "readings": results,
        "anomalies": anomalies,
        "message": (
            "Comparison completed. Flagged readings require investigation; "
            "the comparison does not establish their cause."
        ),
    }