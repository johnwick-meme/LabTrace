"""
tests/test_harness.py — Tests for the LabTrace harness (Programmer 1's components).

These tests verify:
  - Skill and reference files are loaded correctly.
  - Resistance calculations give correct results.
  - The example dataset produces the expected values.
  - The anomalous reading is flagged.
  - Zero current is handled safely.
  - Invalid inputs produce useful errors.
  - The result structure matches the agreed schema.
  - Missing Ollama produces a clear failure (not a fake success).
  - Tool execution appears in the trace.

Tests that need a running LLM are marked and skipped by default.
Run them with:  pytest tests/test_harness.py -m live_model
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# --- Ensure the project root is on sys.path so imports work ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from harness.tools import (
    calculate_resistance_tool,
    compare_readings_tool,
    save_experiment_tool,
    load_experiment_tool,
    search_manual_tool,
)
from harness.agent import (
    run_investigation,
    _load_skill,
    _load_reference,
    _build_prompt,
    _extract_section,
)


# ===================================================================
# Sample data (the example from the spec)
# ===================================================================

SAMPLE_READINGS = [
    {"voltage": 2, "current": 0.02},
    {"voltage": 4, "current": 0.04},
    {"voltage": 6, "current": 0.06},
    {"voltage": 8, "current": 0.04},
]

SAMPLE_EXPERIMENT = {
    "experiment_id": "ohm-001",
    "name": "Ohm's Law Verification",
    "readings": SAMPLE_READINGS,
}


# ===================================================================
# Test: Tool wrappers
# ===================================================================

class TestCalculateResistanceTool(unittest.TestCase):
    """Tests for the calculate_resistance_tool wrapper."""

    def test_normal_calculation(self):
        """2V / 0.02A should give 100 Ω."""
        result = calculate_resistance_tool(2, 0.02)
        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["resistance"], 100.0)
        self.assertIsNone(result["error"])

    def test_first_three_readings_give_100_ohms(self):
        """The first three example readings should all calculate to 100 Ω."""
        for reading in SAMPLE_READINGS[:3]:
            result = calculate_resistance_tool(reading["voltage"], reading["current"])
            self.assertTrue(result["success"])
            self.assertAlmostEqual(result["resistance"], 100.0)

    def test_fourth_reading_gives_200_ohms(self):
        """The last example reading (8V, 0.04A) should give 200 Ω."""
        result = calculate_resistance_tool(8, 0.04)
        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["resistance"], 200.0)

    def test_zero_current_no_crash(self):
        """Zero current should not crash — it should return an error."""
        result = calculate_resistance_tool(5, 0)
        self.assertFalse(result["success"])
        self.assertIsNone(result["resistance"])
        self.assertIn("zero", result["error"].lower())

    def test_invalid_voltage_type(self):
        """Non-numeric voltage should produce a useful error."""
        result = calculate_resistance_tool("five", 0.02)
        self.assertFalse(result["success"])
        self.assertIn("number", result["error"].lower())

    def test_invalid_current_type(self):
        """Non-numeric current should produce a useful error."""
        result = calculate_resistance_tool(5, "bad")
        self.assertFalse(result["success"])
        self.assertIn("number", result["error"].lower())

    def test_original_values_preserved(self):
        """The tool result should echo back the original inputs unchanged."""
        result = calculate_resistance_tool(3.7, 0.015)
        self.assertEqual(result["voltage"], 3.7)
        self.assertEqual(result["current"], 0.015)


class TestCompareReadingsTool(unittest.TestCase):
    """Tests for the compare_readings_tool wrapper."""

    def test_sample_readings_detect_anomaly(self):
        """The fourth reading should be flagged as anomalous."""
        result = compare_readings_tool(SAMPLE_READINGS)
        self.assertTrue(result["success"])
        anomalies = result["result"]["anomalies"]
        self.assertTrue(len(anomalies) > 0, "Expected at least one anomaly")
        # The anomaly should be at index 3 (the fourth reading)
        anomaly_indices = [a["index"] for a in anomalies]
        self.assertIn(3, anomaly_indices)

    def test_raw_data_not_modified(self):
        """compare_readings_tool must not alter the original readings list."""
        readings_copy = [dict(r) for r in SAMPLE_READINGS]
        compare_readings_tool(SAMPLE_READINGS)
        self.assertEqual(SAMPLE_READINGS, readings_copy)

    def test_consistent_readings(self):
        """Three consistent readings should produce no anomalies."""
        readings = [
            {"voltage": 2, "current": 0.02},
            {"voltage": 4, "current": 0.04},
            {"voltage": 6, "current": 0.06},
        ]
        result = compare_readings_tool(readings)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["result"]["anomalies"]), 0)

    def test_empty_list_error(self):
        """An empty readings list should produce an error."""
        result = compare_readings_tool([])
        self.assertFalse(result["success"])
        self.assertIn("empty", result["error"].lower())

    def test_not_a_list_error(self):
        """A non-list input should produce an error."""
        result = compare_readings_tool("not a list")
        self.assertFalse(result["success"])
        self.assertIn("list", result["error"].lower())

    def test_missing_field_error(self):
        """A reading missing 'current' should produce an error."""
        result = compare_readings_tool([{"voltage": 5}])
        self.assertFalse(result["success"])
        self.assertIn("current", result["error"].lower())


class TestSaveLoadTools(unittest.TestCase):
    """Tests for save and load experiment tools."""

    def test_save_and_load(self):
        result = save_experiment_tool(SAMPLE_EXPERIMENT)
        self.assertTrue(result["success"])
        self.assertEqual(result["experiment_id"], "ohm-001")

        loaded = load_experiment_tool("ohm-001")
        self.assertTrue(loaded["success"])
        self.assertEqual(loaded["experiment"]["name"], "Ohm's Law Verification")

    def test_save_missing_id(self):
        result = save_experiment_tool({"name": "no id"})
        self.assertFalse(result["success"])

    def test_load_not_found(self):
        result = load_experiment_tool("nonexistent-999")
        self.assertFalse(result["success"])
        self.assertIn("no experiment found", result["error"].lower())


class TestSearchManualTool(unittest.TestCase):
    """Tests for the search_manual_tool wrapper."""

    def test_basic_search(self):
        manual = "Ohm's law states V=IR.\nResistance is measured in ohms."
        result = search_manual_tool("resistance", manual)
        self.assertTrue(result["success"])
        self.assertTrue(len(result["matches"]) > 0)

    def test_empty_query(self):
        result = search_manual_tool("", "some text")
        self.assertFalse(result["success"])

    def test_no_matches(self):
        result = search_manual_tool("capacitance", "Ohm's law is about resistance.")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["matches"]), 0)


# ===================================================================
# Test: Skill and reference loading
# ===================================================================

class TestFileLoading(unittest.TestCase):
    """Tests that the skill and reference files are actually loaded."""

    def test_skill_file_exists_and_loads(self):
        """SKILL.md should be loadable and non-empty."""
        text, path = _load_skill()
        self.assertIsNotNone(text, f"Could not load skill file at {path}")
        self.assertTrue(len(text) > 100, "Skill file seems too short")
        # It should contain key instruction phrases
        self.assertIn("Preserve original readings", text)

    def test_reference_file_exists_and_loads(self):
        """ohms-law.md should be loadable and non-empty."""
        text, path = _load_reference("ohms-law.md")
        self.assertIsNotNone(text, f"Could not load reference at {path}")
        self.assertTrue(len(text) > 100, "Reference file seems too short")
        # It should contain Ohm's law content
        self.assertIn("V = I", text)

    def test_missing_reference_returns_none(self):
        """A non-existent reference file should return None, not crash."""
        text, path = _load_reference("does-not-exist.md")
        self.assertIsNone(text)


# ===================================================================
# Test: Section extraction
# ===================================================================

class TestSectionExtraction(unittest.TestCase):
    """Tests for _extract_section (best-effort parser)."""

    def test_extract_hypotheses(self):
        text = (
            "## Possible Explanations (Hypotheses)\n"
            "- The resistor may have overheated.\n"
            "- A loose connection is possible.\n"
            "## Next Section\n"
        )
        items = _extract_section(text, "Hypothes")
        self.assertEqual(len(items), 2)
        self.assertIn("overheated", items[0])

    def test_extract_viva_questions(self):
        text = (
            "## Viva Questions\n"
            "1. What is Ohm's law?\n"
            "2. Why might a reading be inconsistent?\n"
        )
        items = _extract_section(text, "Viva")
        self.assertEqual(len(items), 2)

    def test_no_matching_section(self):
        text = "## Unrelated Heading\n- Item\n"
        items = _extract_section(text, "Hypothes")
        self.assertEqual(items, [])


# ===================================================================
# Test: run_investigation (mocked — no real LLM)
# ===================================================================

class TestRunInvestigationMocked(unittest.TestCase):
    """
    Tests for run_investigation() with the Ollama call mocked.
    These do NOT require a running LLM.
    """

    def _mock_ollama_response(self):
        """A fake AI response that follows the expected structure."""
        return (
            "## Experiment Summary\n"
            "This experiment verifies Ohm's law.\n\n"
            "## Calculated Results\n"
            "- Reading 1: R = 100.00 Ω\n"
            "- Reading 2: R = 100.00 Ω\n"
            "- Reading 3: R = 100.00 Ω\n"
            "- Reading 4: R = 200.00 Ω\n\n"
            "## Anomalies Detected\n"
            "- Reading 4 shows R = 200 Ω, double the expected 100 Ω.\n\n"
            "## Evidence and Sources\n"
            "- The first three readings consistently give R = 100 Ω.\n"
            "- Reference: Ohm's law states V = IR.\n\n"
            "## Possible Explanations (Hypotheses)\n"
            "- The resistor may have been changed between readings.\n"
            "- A connection fault may have introduced extra resistance.\n\n"
            "## Recommended Additional Checks\n"
            "- Repeat reading 4.\n"
            "- Measure the resistor with an ohmmeter.\n\n"
            "## Viva Questions\n"
            "1. What is Ohm's law?\n"
            "2. How do you calculate resistance from voltage and current?\n"
            "3. What could cause an anomalous reading?\n"
        )

    @patch("harness.agent._call_ollama")
    def test_successful_investigation(self, mock_ollama):
        """A mocked successful investigation should return status='success'."""
        mock_ollama.return_value = (self._mock_ollama_response(), None)

        result = run_investigation(SAMPLE_EXPERIMENT)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["experiment_id"], "ohm-001")
        self.assertTrue(len(result["report"]) > 0)
        self.assertTrue(len(result["calculations"]) == 4)
        self.assertTrue(len(result["anomalies"]) > 0)
        self.assertTrue(len(result["viva_questions"]) > 0)

    @patch("harness.agent._call_ollama")
    def test_result_structure(self, mock_ollama):
        """The result must have all agreed keys."""
        mock_ollama.return_value = (self._mock_ollama_response(), None)

        result = run_investigation(SAMPLE_EXPERIMENT)

        expected_keys = {
            "status", "experiment_id", "report", "calculations",
            "anomalies", "evidence", "hypotheses", "viva_questions",
            "trace", "errors",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    @patch("harness.agent._call_ollama")
    def test_trace_contains_tool_calls(self, mock_ollama):
        """The trace should record skill loading, calculations, and model call."""
        mock_ollama.return_value = (self._mock_ollama_response(), None)

        result = run_investigation(SAMPLE_EXPERIMENT)

        trace_steps = [t["step"] for t in result["trace"]]
        self.assertIn("validate_input", trace_steps)
        self.assertIn("load_skill", trace_steps)
        self.assertIn("load_reference", trace_steps)
        self.assertIn("calculate_resistances", trace_steps)
        self.assertIn("compare_readings", trace_steps)
        self.assertIn("call_gemma", trace_steps)

    @patch("harness.agent._call_ollama")
    def test_calculations_correct(self, mock_ollama):
        """The deterministic calculations should be correct regardless of AI."""
        mock_ollama.return_value = (self._mock_ollama_response(), None)

        result = run_investigation(SAMPLE_EXPERIMENT)

        # First three readings: 100 Ω each
        for calc in result["calculations"][:3]:
            self.assertAlmostEqual(calc["resistance"], 100.0)
        # Fourth reading: 200 Ω
        self.assertAlmostEqual(result["calculations"][3]["resistance"], 200.0)

    @patch("harness.agent._call_ollama")
    def test_anomaly_flagged_without_modifying_data(self, mock_ollama):
        """The anomaly should be flagged, but original readings untouched."""
        mock_ollama.return_value = (self._mock_ollama_response(), None)

        original_readings = [dict(r) for r in SAMPLE_READINGS]
        experiment = {**SAMPLE_EXPERIMENT, "readings": SAMPLE_READINGS}

        result = run_investigation(experiment)

        # Anomaly at index 3 should be detected
        anomaly_indices = [a["index"] for a in result["anomalies"]]
        self.assertIn(3, anomaly_indices)

        # Original readings should be unchanged
        self.assertEqual(SAMPLE_READINGS, original_readings)

    @patch("harness.agent._call_ollama")
    def test_ollama_failure_no_fake_success(self, mock_ollama):
        """If Ollama fails, status must NOT be 'success'."""
        mock_ollama.return_value = (None, "Connection refused")

        result = run_investigation(SAMPLE_EXPERIMENT)

        self.assertNotEqual(result["status"], "success")
        self.assertEqual(result["status"], "partial")
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("Gemma", result["errors"][0])

    @patch("harness.agent._call_ollama")
    def test_ollama_failure_still_has_calculations(self, mock_ollama):
        """Even if the AI fails, deterministic calculations should be present."""
        mock_ollama.return_value = (None, "Timeout")

        result = run_investigation(SAMPLE_EXPERIMENT)

        self.assertEqual(len(result["calculations"]), 4)
        self.assertAlmostEqual(result["calculations"][0]["resistance"], 100.0)

    def test_invalid_experiment_not_dict(self):
        """Passing a non-dict should return an error, not crash."""
        result = run_investigation("not a dict")
        self.assertEqual(result["status"], "error")
        self.assertTrue(len(result["errors"]) > 0)

    def test_missing_experiment_id(self):
        """Missing experiment_id should return an error."""
        result = run_investigation({"readings": [{"voltage": 1, "current": 0.01}]})
        self.assertEqual(result["status"], "error")

    def test_empty_readings(self):
        """Empty readings list should return an error."""
        result = run_investigation({"experiment_id": "x", "readings": []})
        self.assertEqual(result["status"], "error")

    @patch("harness.agent._call_ollama")
    def test_zero_current_in_readings(self, mock_ollama):
        """A reading with zero current should not crash the investigation."""
        mock_ollama.return_value = ("## Report\n- Incomplete data.\n", None)

        experiment = {
            "experiment_id": "zero-test",
            "name": "Zero Current Test",
            "readings": [
                {"voltage": 5, "current": 0},
                {"voltage": 10, "current": 0.1},
            ],
        }
        result = run_investigation(experiment)

        # Should not crash
        self.assertIn(result["status"], ("success", "partial"))
        # First calculation should have an error
        self.assertIsNone(result["calculations"][0]["resistance"])
        self.assertIsNotNone(result["calculations"][0]["error"])
        # Second calculation should succeed
        self.assertAlmostEqual(result["calculations"][1]["resistance"], 100.0)

    @patch("harness.agent._call_ollama")
    def test_tool_errors_in_trace(self, mock_ollama):
        """Tool errors should appear in the trace."""
        mock_ollama.return_value = ("## Report\n", None)

        experiment = {
            "experiment_id": "trace-test",
            "name": "Trace Test",
            "readings": [{"voltage": 5, "current": 0}],  # will cause error
        }
        result = run_investigation(experiment)

        # Find the calculate_resistances trace entry
        calc_trace = [t for t in result["trace"]
                      if t["step"] == "calculate_resistances"]
        self.assertTrue(len(calc_trace) > 0)
        # The outputs should show an error for the zero-current reading
        outputs = calc_trace[0].get("outputs", [])
        self.assertTrue(any(o.get("error") is not None for o in outputs))


# ===================================================================
# Test: Live model (requires running Ollama + Gemma)
# ===================================================================

# These tests are skipped by default.  Run them with:
#   pytest tests/test_harness.py -m live_model -v

live_model = unittest.skipUnless(
    os.environ.get("LABTRACE_LIVE_MODEL_TESTS") == "1",
    "Live model tests skipped (set LABTRACE_LIVE_MODEL_TESTS=1 to run)",
)


@live_model
class TestRunInvestigationLive(unittest.TestCase):
    """Tests that actually call the local Gemma model."""

    def test_live_investigation(self):
        """Run a real investigation and check the result structure."""
        result = run_investigation(SAMPLE_EXPERIMENT)

        self.assertEqual(result["status"], "success")
        self.assertTrue(len(result["report"]) > 50)
        self.assertEqual(len(result["calculations"]), 4)
        print(result["report"][:1000].encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))


if __name__ == "__main__":
    unittest.main()
