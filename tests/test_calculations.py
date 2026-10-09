"""
tests/test_calculations.py — Unit tests for core.calculations.

Run with:   pytest tests/test_calculations.py -v
(from the project root: LabTrace_UI_Starter/)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from core.calculations import calculate_resistance, compare_readings, calculate_experiment


# ===========================================================================
# calculate_resistance
# ===========================================================================

class TestCalculateResistance:
    """Tests for the core Ohm's law function R = V / I."""

    # --- Normal inputs ---

    def test_basic(self):
        assert calculate_resistance(10.0, 2.0) == pytest.approx(5.0)

    def test_integer_inputs(self):
        assert calculate_resistance(6, 3) == pytest.approx(2.0)

    def test_small_current(self):
        assert calculate_resistance(2.0, 0.02) == pytest.approx(100.0)

    def test_high_resistance(self):
        assert calculate_resistance(230.0, 0.001) == pytest.approx(230_000.0)

    def test_zero_voltage(self):
        # R = 0 / I = 0 is physically valid
        assert calculate_resistance(0.0, 1.0) == pytest.approx(0.0)

    def test_string_numbers_are_accepted(self):
        # Tolerant parsing: "10" and "2" should work
        assert calculate_resistance("10", "2") == pytest.approx(5.0)

    # --- Edge cases ---

    def test_very_small_current(self):
        # Should not raise; result is a large number
        result = calculate_resistance(1.0, 1e-9)
        assert result == pytest.approx(1e9)

    def test_fractional_values(self):
        assert calculate_resistance(3.3, 0.033) == pytest.approx(100.0, rel=1e-4)

    # --- Invalid inputs: zero current ---

    def test_zero_current_raises_value_error(self):
        with pytest.raises(ValueError, match="cannot be zero"):
            calculate_resistance(5.0, 0.0)

    def test_zero_current_int_raises(self):
        with pytest.raises(ValueError):
            calculate_resistance(10, 0)

    # --- Invalid inputs: negative values ---

    def test_negative_voltage_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            calculate_resistance(-5.0, 2.0)

    def test_negative_current_raises(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            calculate_resistance(5.0, -1.0)

    # --- Invalid inputs: non-numeric ---

    def test_string_voltage_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_resistance("five", 2.0)

    def test_none_current_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_resistance(5.0, None)

    def test_list_input_raises_type_error(self):
        with pytest.raises(TypeError):
            calculate_resistance([5.0], 2.0)


# ===========================================================================
# compare_readings
# ===========================================================================

class TestCompareReadings:
    """Tests for the multi-reading comparison function."""

    def _ohms_readings(self, pairs: list[tuple]) -> list[dict]:
        return [{"voltage_v": v, "current_a": i} for v, i in pairs]

    # --- Normal inputs ---

    def test_all_consistent(self):
        readings = self._ohms_readings([(2.0, 0.02), (4.0, 0.04), (6.0, 0.06)])
        result = compare_readings(readings)
        assert result["valid_count"] == 3
        assert result["discrepancies"] == []
        assert result["baseline_mean_ohm"] == pytest.approx(100.0, rel=1e-4)

    def test_single_reading(self):
        readings = self._ohms_readings([(5.0, 0.05)])
        result = compare_readings(readings)
        assert result["valid_count"] == 1
        assert result["baseline_mean_ohm"] == pytest.approx(100.0)

    def test_discrepancy_detected(self):
        # Trials 1–3 give 100 Ω; trial 4 gives 200 Ω (100 % deviation)
        readings = self._ohms_readings([(2.0, 0.02), (4.0, 0.04), (6.0, 0.06), (8.0, 0.04)])
        result = compare_readings(readings)
        assert len(result["discrepancies"]) == 1
        assert result["discrepancies"][0]["trial"] == 4
        assert result["discrepancies"][0]["deviation_pct"] == pytest.approx(100.0, rel=0.01)

    def test_no_discrepancy_below_threshold(self):
        # 10 % deviation — below the 20 % threshold
        readings = self._ohms_readings([(2.0, 0.02), (4.0, 0.04), (6.0, 0.06), (6.6, 0.06)])
        result = compare_readings(readings)
        assert result["discrepancies"] == []

    def test_rows_count_matches_input(self):
        readings = self._ohms_readings([(1, 0.01), (2, 0.02), (3, 0.03), (4, 0.04)])
        result = compare_readings(readings)
        assert len(result["rows"]) == 4

    def test_resistance_values_in_rows(self):
        readings = self._ohms_readings([(10.0, 0.1), (20.0, 0.2)])
        result = compare_readings(readings)
        assert result["rows"][0]["resistance_ohm"] == pytest.approx(100.0)
        assert result["rows"][1]["resistance_ohm"] == pytest.approx(100.0)

    def test_row_status_ok_for_valid(self):
        readings = self._ohms_readings([(5.0, 0.05)])
        result = compare_readings(readings)
        assert result["rows"][0]["status"] == "ok"

    def test_alternative_key_names(self):
        # Support 'voltage'/'current' aliases
        readings = [{"voltage": 10.0, "current": 0.1}]
        result = compare_readings(readings)
        assert result["rows"][0]["resistance_ohm"] == pytest.approx(100.0)

    # --- Zero current in a reading ---

    def test_zero_current_row_marked_invalid(self):
        readings = [{"voltage_v": 5.0, "current_a": 0.0}]
        result = compare_readings(readings)
        assert result["rows"][0]["resistance_ohm"] is None
        assert result["valid_count"] == 0

    # --- Invalid arguments ---

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            compare_readings([])

    def test_not_a_list_raises(self):
        with pytest.raises(TypeError):
            compare_readings("not a list")

    def test_none_raises(self):
        with pytest.raises(TypeError):
            compare_readings(None)

    def test_bad_dict_in_list_is_skipped(self):
        readings = [{"voltage_v": 5.0, "current_a": 0.05}, "bad", {"voltage_v": 10.0, "current_a": 0.1}]
        result = compare_readings(readings)
        # "bad" string should be in rows with status=skipped, not crash
        assert len(result["rows"]) == 3
        assert result["rows"][1]["resistance_ohm"] is None
        assert "skipped" in result["rows"][1]["status"]


# ===========================================================================
# calculate_experiment (integration wrapper)
# ===========================================================================

class TestCalculateExperiment:
    """Tests for the app.py adapter wrapper."""

    def test_returns_dict(self):
        payload = {"title": "Test", "readings": [{"voltage_v": 5.0, "current_a": 0.05}]}
        result = calculate_experiment(payload)
        assert isinstance(result, dict)

    def test_rows_present(self):
        payload = {"readings": [{"voltage_v": 5.0, "current_a": 0.05}]}
        result = calculate_experiment(payload)
        assert "rows" in result
        assert len(result["rows"]) == 1

    def test_mode_field_is_deterministic(self):
        payload = {"readings": [{"voltage_v": 5.0, "current_a": 0.05}]}
        result = calculate_experiment(payload)
        assert "deterministic" in result["mode"].lower()

    def test_title_preserved(self):
        payload = {"title": "My experiment", "readings": [{"voltage_v": 1.0, "current_a": 0.01}]}
        result = calculate_experiment(payload)
        assert result["title"] == "My experiment"

    def test_no_readings_raises(self):
        with pytest.raises(ValueError, match="readings"):
            calculate_experiment({"title": "No readings"})

    def test_empty_readings_raises(self):
        with pytest.raises(ValueError):
            calculate_experiment({"readings": []})

    def test_none_payload_raises(self):
        with pytest.raises(ValueError):
            calculate_experiment(None)

    def test_kwargs_calling_convention(self):
        # app.py uses _call_compatible which may pass as kwargs
        result = calculate_experiment(
            readings=[{"voltage_v": 10.0, "current_a": 0.1}],
            title="kwargs test"
        )
        assert result["rows"][0]["resistance_ohm"] == pytest.approx(100.0)

    def test_discrepancy_propagates(self):
        payload = {
            "readings": [
                {"voltage_v": 2.0, "current_a": 0.02},
                {"voltage_v": 4.0, "current_a": 0.04},
                {"voltage_v": 6.0, "current_a": 0.06},
                {"voltage_v": 8.0, "current_a": 0.04},   # diverges
            ]
        }
        result = calculate_experiment(payload)
        assert len(result["discrepancies"]) == 1
