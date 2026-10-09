"""
harness/tools.py — Controlled tool interface for the investigation agent.

This module wraps the shared functions from core/calculations.py and
core/memory.py, adding:
  - Input validation
  - Safe error handling (zero current, missing fields, bad types)
  - Structured return values
  - Protection against the LLM silently altering original data

The agent harness calls these functions — the LLM never calls them
directly or executes arbitrary code.
"""

from core.calculations import calculate_resistance, compare_readings
from core.memory import save_experiment, load_experiment, search_manual


# ---------------------------------------------------------------------------
# Tool wrapper: calculate_resistance_tool
# ---------------------------------------------------------------------------

def calculate_resistance_tool(voltage, current):
    """
    Safely calculate resistance for a single (voltage, current) pair.

    Returns a dict:
        {
            "success": True/False,
            "voltage": <original voltage>,
            "current": <original current>,
            "resistance": <calculated value or None>,
            "error": <error message or None>
        }
    """
    result = {
        "success": False,
        "voltage": voltage,
        "current": current,
        "resistance": None,
        "error": None,
    }

    # --- Validate types ---
    if not isinstance(voltage, (int, float)):
        result["error"] = f"Voltage must be a number, got {type(voltage).__name__}."
        return result
    if not isinstance(current, (int, float)):
        result["error"] = f"Current must be a number, got {type(current).__name__}."
        return result

    # --- Handle zero current ---
    if current == 0:
        result["error"] = (
            "Current is zero — resistance cannot be calculated. "
            "This may indicate an open circuit or a faulty reading."
        )
        return result

    # --- Delegate to the deterministic function ---
    try:
        raw_res = calculate_resistance(voltage, current)
        # Handle both float and dict return from calculate_resistance
        if isinstance(raw_res, dict):
            resistance = raw_res.get("resistance_ohm")
        else:
            resistance = raw_res
        result["success"] = True
        result["resistance"] = resistance
    except Exception as exc:
        result["error"] = f"Calculation failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Tool wrapper: compare_readings_tool
# ---------------------------------------------------------------------------

def compare_readings_tool(readings):
    """
    Safely compare a list of readings and detect anomalies.

    Parameters:
        readings: list of dicts, each with "voltage" and "current" keys.

    Returns a dict:
        {
            "success": True/False,
            "result": <output from compare_readings() or None>,
            "error": <error message or None>
        }
    """
    result = {
        "success": False,
        "result": None,
        "error": None,
    }

    # --- Validate that readings is a non-empty list ---
    if not isinstance(readings, list):
        result["error"] = f"readings must be a list, got {type(readings).__name__}."
        return result
    if len(readings) == 0:
        result["error"] = "readings list is empty — nothing to compare."
        return result

    # --- Validate each reading ---
    normalized_readings = []
    for i, reading in enumerate(readings):
        if not isinstance(reading, dict):
            result["error"] = f"Reading {i} is not a dict: {reading!r}"
            return result
        v = reading.get("voltage", reading.get("voltage_v"))
        c = reading.get("current", reading.get("current_a"))
        if v is None:
            result["error"] = f"Reading {i} is missing the 'voltage' field."
            return result
        if c is None:
            result["error"] = f"Reading {i} is missing the 'current' field."
            return result
        if not isinstance(v, (int, float)):
            result["error"] = (
                f"Reading {i}: voltage must be a number, "
                f"got {type(v).__name__}."
            )
            return result
        if not isinstance(c, (int, float)):
            result["error"] = (
                f"Reading {i}: current must be a number, "
                f"got {type(c).__name__}."
            )
            return result
        
        norm_r = dict(reading)
        norm_r["voltage"] = v
        norm_r["voltage_v"] = v
        norm_r["current"] = c
        norm_r["current_a"] = c
        norm_r["reading_id"] = reading.get("reading_id", f"R{i + 1}")
        normalized_readings.append(norm_r)

    # --- Delegate to the deterministic function ---
    try:
        comparison = compare_readings(normalized_readings)
        
        # Normalize comparison return if it's from Programmer 2's structure
        if "reference_resistance_ohm" in comparison:
            norm_anomalies = []
            for idx, r_item in enumerate(comparison.get("readings", [])):
                if r_item.get("anomaly"):
                    calc_dict = r_item.get("calculation") or {}
                    res_val = calc_dict.get("resistance_ohm")
                    ref_val = comparison.get("reference_resistance_ohm")
                    dev_pct = round((r_item.get("deviation_fraction") or 0) * 100, 1)
                    norm_anomalies.append({
                        "index": idx,
                        "reading_id": r_item.get("reading_id"),
                        "reading": normalized_readings[idx],
                        "resistance": res_val,
                        "expected": ref_val,
                        "deviation_pct": dev_pct,
                        "reason": f"Resistance ({res_val:.2f} Ω) deviates {dev_pct}% from median ({ref_val:.2f} Ω).",
                    })
            consistent_count = sum(1 for r_item in comparison.get("readings", []) if not r_item.get("anomaly") and r_item.get("valid"))
            comparison = {
                "resistances": [r_item.get("calculation", {}).get("resistance_ohm") if r_item.get("calculation") else None for r_item in comparison.get("readings", [])],
                "median_resistance": comparison.get("reference_resistance_ohm"),
                "anomalies": norm_anomalies,
                "consistent_count": consistent_count,
                "raw_result": comparison,
            }

        result["success"] = True
        result["result"] = comparison
    except Exception as exc:
        result["error"] = f"Comparison failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Tool wrapper: save_experiment_tool
# ---------------------------------------------------------------------------

def save_experiment_tool(experiment):
    """
    Safely persist an experiment record.

    Returns a dict:
        {
            "success": True/False,
            "experiment_id": <id or None>,
            "error": <error message or None>
        }
    """
    result = {
        "success": False,
        "experiment_id": None,
        "error": None,
    }

    if not isinstance(experiment, dict):
        result["error"] = f"experiment must be a dict, got {type(experiment).__name__}."
        return result
    if "experiment_id" not in experiment:
        result["error"] = "experiment must have an 'experiment_id' field."
        return result

    try:
        raw_save = save_experiment(experiment)
        if isinstance(raw_save, dict):
            exp_id = raw_save.get("experiment_id")
        else:
            exp_id = raw_save
        result["success"] = True
        result["experiment_id"] = exp_id
    except Exception as exc:
        result["error"] = f"Save failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Tool wrapper: load_experiment_tool
# ---------------------------------------------------------------------------

def load_experiment_tool(experiment_id):
    """
    Safely load a previously saved experiment.

    Returns a dict:
        {
            "success": True/False,
            "experiment": <experiment dict or None>,
            "error": <error message or None>
        }
    """
    result = {
        "success": False,
        "experiment": None,
        "error": None,
    }

    if not experiment_id:
        result["error"] = "experiment_id is required."
        return result

    try:
        exp = load_experiment(experiment_id)
        if exp is None:
            result["error"] = f"No experiment found with id '{experiment_id}'."
        else:
            result["success"] = True
            result["experiment"] = exp
    except Exception as exc:
        result["error"] = f"Load failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Tool wrapper: search_manual_tool
# ---------------------------------------------------------------------------

def search_manual_tool(query, manual_text):
    """
    Safely search the manual/reference text.

    Returns a dict:
        {
            "success": True/False,
            "matches": <list of matching lines or []>,
            "error": <error message or None>
        }
    """
    result = {
        "success": False,
        "matches": [],
        "error": None,
    }

    if not isinstance(query, str) or not query.strip():
        result["error"] = "query must be a non-empty string."
        return result
    if not isinstance(manual_text, str):
        result["error"] = "manual_text must be a string."
        return result

    try:
        matches = search_manual(query, manual_text)
        result["success"] = True
        result["matches"] = matches
    except Exception as exc:
        result["error"] = f"Search failed: {exc}"

    return result
