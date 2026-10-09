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
        resistance = calculate_resistance(voltage, current)
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
    for i, reading in enumerate(readings):
        if not isinstance(reading, dict):
            result["error"] = f"Reading {i} is not a dict: {reading!r}"
            return result
        if "voltage" not in reading:
            result["error"] = f"Reading {i} is missing the 'voltage' field."
            return result
        if "current" not in reading:
            result["error"] = f"Reading {i} is missing the 'current' field."
            return result
        if not isinstance(reading["voltage"], (int, float)):
            result["error"] = (
                f"Reading {i}: voltage must be a number, "
                f"got {type(reading['voltage']).__name__}."
            )
            return result
        if not isinstance(reading["current"], (int, float)):
            result["error"] = (
                f"Reading {i}: current must be a number, "
                f"got {type(reading['current']).__name__}."
            )
            return result

    # --- Delegate to the deterministic function ---
    try:
        comparison = compare_readings(readings)
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
        exp_id = save_experiment(experiment)
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
