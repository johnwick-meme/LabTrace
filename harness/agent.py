"""
harness/agent.py — Main investigation agent for LabTrace.

Entry point:
    run_investigation(experiment) -> dict

This module orchestrates the entire investigation workflow:
  1. Validate the experiment input.
  2. Load the Agent Skill (SKILL.md) and relevant reference documents.
  3. Run deterministic calculation tools on the readings.
  4. Build a structured prompt with the data, tool results, and skill.
  5. Call the local Gemma model through Ollama.
  6. Validate and structure the response.
  7. Return a traceable result dict.

The LLM does NOT call tools itself — the harness runs them first and
provides the results as context.
"""

import json
import os
import time
import traceback

import requests

import config
from harness.tools import (
    calculate_resistance_tool,
    compare_readings_tool,
    save_experiment_tool,
    search_manual_tool,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_path(relative_path):
    """
    Resolve a path relative to the project root.

    The project root is assumed to be the directory containing config.py.
    """
    project_root = os.path.dirname(os.path.abspath(config.__file__))
    return os.path.join(project_root, relative_path)


def _load_text_file(path):
    """Read a text file and return its content, or None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _load_skill():
    """Load the SKILL.md file and return its text."""
    path = _resolve_path(config.SKILL_PATH)
    return _load_text_file(path), path


def _load_reference(filename):
    """Load a reference document from the references directory."""
    path = _resolve_path(os.path.join(config.REFERENCES_DIR, filename))
    return _load_text_file(path), path


def _make_trace_entry(step, detail=None, inputs=None, outputs=None, error=None):
    """Create a single trace entry."""
    entry = {"step": step, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if detail:
        entry["detail"] = detail
    if inputs is not None:
        entry["inputs"] = inputs
    if outputs is not None:
        entry["outputs"] = outputs
    if error:
        entry["error"] = error
    return entry


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_prompt(experiment, skill_text, reference_text, calc_results, comparison_result):
    """
    Build the structured prompt that will be sent to Gemma.

    The prompt includes:
      - The skill instructions (how the agent should behave).
      - The reference material (theory).
      - The original experiment readings (read-only).
      - The deterministic calculation results.
      - The comparison / anomaly detection results.
      - A clear instruction to produce the report.
    """
    sections = []

    # 1. Skill instructions
    sections.append("=== AGENT SKILL INSTRUCTIONS ===")
    sections.append(skill_text)
    sections.append("")

    # 2. Reference material
    if reference_text:
        sections.append("=== REFERENCE MATERIAL ===")
        sections.append(reference_text)
        sections.append("")

    # 3. Experiment details
    sections.append("=== EXPERIMENT ===")
    sections.append(f"Experiment ID: {experiment.get('experiment_id', 'unknown')}")
    sections.append(f"Experiment Name: {experiment.get('name', 'unknown')}")
    sections.append("")
    sections.append("Original readings (DO NOT modify these):")
    for i, reading in enumerate(experiment.get("readings", [])):
        sections.append(f"  Reading {i + 1}: Voltage = {reading.get('voltage')} V, "
                        f"Current = {reading.get('current')} A")
    sections.append("")

    # 4. Deterministic calculation results
    sections.append("=== TOOL RESULTS: Individual Resistance Calculations ===")
    for cr in calc_results:
        if cr["success"]:
            sections.append(
                f"  V={cr['voltage']} V, I={cr['current']} A → "
                f"R = {cr['resistance']:.2f} Ω"
            )
        else:
            sections.append(
                f"  V={cr['voltage']} V, I={cr['current']} A → "
                f"ERROR: {cr['error']}"
            )
    sections.append("")

    # 5. Comparison / anomaly results
    sections.append("=== TOOL RESULTS: Reading Comparison ===")
    if comparison_result["success"]:
        comp = comparison_result["result"]
        median_r = comp['median_resistance']
        if median_r is not None:
            sections.append(f"  Median resistance: {median_r:.2f} Ω")
        else:
            sections.append("  Median resistance: N/A (no valid readings)")
        sections.append(f"  Consistent readings: {comp['consistent_count']}")
        if comp["anomalies"]:
            sections.append(f"  Anomalies detected: {len(comp['anomalies'])}")
            for a in comp["anomalies"]:
                sections.append(f"    - Reading {a['index'] + 1}: {a['reason']}")
        else:
            sections.append("  No anomalies detected.")
    else:
        sections.append(f"  Comparison failed: {comparison_result['error']}")
    sections.append("")

    # 6. Task instruction
    sections.append("=== YOUR TASK ===")
    sections.append(
        "Using the skill instructions, reference material, original readings, "
        "and the deterministic tool results above, produce a complete "
        "investigation report.  Follow the report structure defined in the "
        "skill instructions.  Do NOT recalculate any numbers — use the tool "
        "results exactly as given.  Label any explanations that are not "
        "directly supported by evidence as hypotheses."
    )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Ollama interaction
# ---------------------------------------------------------------------------

def _call_ollama(prompt, model=None, timeout=None):
    """
    Send a prompt to the local Ollama API and return the response text.

    Returns:
        (response_text, error_message)
        On success:  (str, None)
        On failure:  (None, str)
    """
    model = model or config.OLLAMA_MODEL
    timeout = timeout or config.OLLAMA_TIMEOUT
    url = f"{config.OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=timeout)
    except requests.ConnectionError:
        return None, (
            "Could not connect to Ollama. "
            "Make sure Ollama is running (start it with: ollama serve). "
            f"Expected URL: {config.OLLAMA_BASE_URL}"
        )
    except requests.Timeout:
        return None, (
            f"Ollama request timed out after {timeout} seconds. "
            "The model may be too large for this machine, or Ollama may be "
            "overloaded.  Try a smaller model or increase LABTRACE_OLLAMA_TIMEOUT."
        )
    except Exception as exc:
        return None, f"Unexpected error contacting Ollama: {exc}"

    if resp.status_code != 200:
        return None, (
            f"Ollama returned HTTP {resp.status_code}. "
            f"Response body: {resp.text[:500]}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return None, "Ollama returned a non-JSON response."

    response_text = data.get("response", "").strip()
    if not response_text:
        return None, "Ollama returned an empty response."

    return response_text, None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_investigation(experiment):
    """
    Run a full laboratory investigation on the given experiment.

    Parameters:
        experiment (dict): Must contain:
            - experiment_id (str): Unique identifier.
            - name (str): Human-readable experiment name.
            - readings (list[dict]): Each dict has "voltage" and "current".
            Optionally:
            - manual_text (str): Reference text (if not supplied, the
              harness loads the appropriate reference file).
            - reference_file (str): Filename in the references/ directory
              to load (default: "ohms-law.md").

    Returns:
        dict: Structured investigation result with keys:
            status, experiment_id, report, calculations, anomalies,
            evidence, hypotheses, viva_questions, trace, errors.
    """

    # --- Initialise the result structure ---
    result = {
        "status": "error",  # will be set to "success" only if everything works
        "experiment_id": None,
        "report": "",
        "calculations": [],
        "anomalies": [],
        "evidence": [],
        "hypotheses": [],
        "viva_questions": [],
        "trace": [],
        "errors": [],
    }

    # -----------------------------------------------------------------------
    # Step 0: Validate experiment input
    # -----------------------------------------------------------------------
    if not isinstance(experiment, dict):
        result["errors"].append("experiment must be a dict.")
        result["trace"].append(_make_trace_entry(
            "validate_input", error="experiment is not a dict"))
        return result

    exp_id = experiment.get("experiment_id")
    if not exp_id:
        result["errors"].append("experiment must have an 'experiment_id'.")
        result["trace"].append(_make_trace_entry(
            "validate_input", error="missing experiment_id"))
        return result
    result["experiment_id"] = exp_id

    readings = experiment.get("readings")
    if not isinstance(readings, list) or len(readings) == 0:
        result["errors"].append("experiment must have a non-empty 'readings' list.")
        result["trace"].append(_make_trace_entry(
            "validate_input", error="missing or empty readings"))
        return result

    result["trace"].append(_make_trace_entry(
        "validate_input",
        detail=f"Experiment '{exp_id}' with {len(readings)} readings.",
    ))

    # -----------------------------------------------------------------------
    # Step 1: Load Agent Skill
    # -----------------------------------------------------------------------
    skill_text, skill_path = _load_skill()
    if not skill_text:
        result["errors"].append(f"Could not load skill file at: {skill_path}")
        result["trace"].append(_make_trace_entry(
            "load_skill", error=f"File not found: {skill_path}"))
        return result

    result["trace"].append(_make_trace_entry(
        "load_skill",
        detail=f"Loaded {len(skill_text)} chars from {skill_path}",
    ))

    # -----------------------------------------------------------------------
    # Step 2: Load reference material
    # -----------------------------------------------------------------------
    ref_filename = experiment.get("reference_file", "ohms-law.md")
    manual_text = experiment.get("manual_text")
    ref_path = None

    if not manual_text:
        manual_text, ref_path = _load_reference(ref_filename)

    if manual_text:
        result["trace"].append(_make_trace_entry(
            "load_reference",
            detail=f"Loaded reference '{ref_filename}' ({len(manual_text)} chars)"
                   + (f" from {ref_path}" if ref_path else " (supplied in experiment)"),
        ))
    else:
        # Not fatal — we can still investigate without reference text
        result["trace"].append(_make_trace_entry(
            "load_reference",
            detail=f"No reference text available (tried '{ref_filename}').",
        ))

    # -----------------------------------------------------------------------
    # Step 3: Run deterministic calculations
    # -----------------------------------------------------------------------
    calc_results = []
    for i, reading in enumerate(readings):
        v = reading.get("voltage")
        c = reading.get("current")
        cr = calculate_resistance_tool(v, c)
        calc_results.append(cr)

        result["calculations"].append({
            "reading_index": i,
            "voltage": v,
            "current": c,
            "resistance": cr.get("resistance"),
            "error": cr.get("error"),
        })

    result["trace"].append(_make_trace_entry(
        "calculate_resistances",
        detail=f"Calculated resistance for {len(readings)} readings.",
        inputs=[{"voltage": r.get("voltage"), "current": r.get("current")}
                for r in readings],
        outputs=[{"resistance": cr.get("resistance"), "error": cr.get("error")}
                 for cr in calc_results],
    ))

    # -----------------------------------------------------------------------
    # Step 4: Compare readings and detect anomalies
    # -----------------------------------------------------------------------
    comparison = compare_readings_tool(readings)
    if comparison["success"]:
        result["anomalies"] = comparison["result"].get("anomalies", [])
    else:
        result["errors"].append(f"Comparison failed: {comparison.get('error')}")

    result["trace"].append(_make_trace_entry(
        "compare_readings",
        detail="Compared readings for anomalies.",
        outputs=comparison,
    ))

    # -----------------------------------------------------------------------
    # Step 5: Build prompt and call Gemma
    # -----------------------------------------------------------------------
    prompt = _build_prompt(
        experiment, skill_text, manual_text, calc_results, comparison
    )
    result["trace"].append(_make_trace_entry(
        "build_prompt",
        detail=f"Prompt built ({len(prompt)} chars).",
    ))

    report_text, ollama_error = _call_ollama(prompt)

    if ollama_error:
        result["errors"].append(f"Gemma/Ollama error: {ollama_error}")
        result["trace"].append(_make_trace_entry(
            "call_gemma", error=ollama_error))
        # Even without AI, we still have the deterministic results.
        # Build a minimal report from what we have.
        result["report"] = _fallback_report(experiment, calc_results, comparison)
        result["status"] = "partial"
        result["trace"].append(_make_trace_entry(
            "fallback_report",
            detail="Generated a deterministic-only report (no AI analysis).",
        ))
        return result

    result["trace"].append(_make_trace_entry(
        "call_gemma",
        detail=f"Received {len(report_text)} chars from model '{config.OLLAMA_MODEL}'.",
    ))

    # -----------------------------------------------------------------------
    # Step 6: Validate and structure the AI response
    # -----------------------------------------------------------------------
    result["report"] = report_text

    # Extract sections from the AI's free-text report (best-effort).
    # The AI is instructed to use specific headings, so we look for them.
    result["evidence"] = _extract_section(report_text, "Evidence")
    result["hypotheses"] = _extract_section(report_text, "Hypothes")
    result["viva_questions"] = _extract_section(report_text, "Viva")

    # -----------------------------------------------------------------------
    # Step 7: Save the experiment (with results attached)
    # -----------------------------------------------------------------------
    experiment_to_save = {
        **experiment,
        "investigation_result": {
            "calculations": result["calculations"],
            "anomalies": result["anomalies"],
        },
    }
    save_result = save_experiment_tool(experiment_to_save)
    result["trace"].append(_make_trace_entry(
        "save_experiment",
        detail=f"Saved experiment '{exp_id}'." if save_result["success"]
               else f"Save failed: {save_result.get('error')}",
    ))

    # -----------------------------------------------------------------------
    # Done — mark success
    # -----------------------------------------------------------------------
    result["status"] = "success"
    return result


# ---------------------------------------------------------------------------
# Fallback report (when Gemma is unavailable)
# ---------------------------------------------------------------------------

def _fallback_report(experiment, calc_results, comparison):
    """
    Generate a minimal report using only deterministic results.
    Used when the AI model is not available.
    """
    lines = []
    lines.append("# Investigation Report (Deterministic Only)")
    lines.append("")
    lines.append("**Note:** The AI model (Gemma via Ollama) was not available. "
                 "This report contains only the deterministic calculation results.")
    lines.append("")

    lines.append("## Experiment")
    lines.append(f"- ID: {experiment.get('experiment_id', 'unknown')}")
    lines.append(f"- Name: {experiment.get('name', 'unknown')}")
    lines.append("")

    lines.append("## Original Readings")
    for i, r in enumerate(experiment.get("readings", [])):
        lines.append(f"- Reading {i+1}: V = {r.get('voltage')} V, "
                     f"I = {r.get('current')} A")
    lines.append("")

    lines.append("## Calculated Resistances")
    for cr in calc_results:
        if cr["success"]:
            lines.append(f"- V = {cr['voltage']} V, I = {cr['current']} A "
                         f"→ R = {cr['resistance']:.2f} Ω")
        else:
            lines.append(f"- V = {cr['voltage']} V, I = {cr['current']} A "
                         f"→ Error: {cr['error']}")
    lines.append("")

    if comparison["success"]:
        comp = comparison["result"]
        lines.append("## Anomalies")
        if comp["anomalies"]:
            for a in comp["anomalies"]:
                lines.append(f"- Reading {a['index']+1}: {a['reason']}")
        else:
            lines.append("- No anomalies detected.")
    else:
        lines.append("## Anomalies")
        lines.append(f"- Comparison failed: {comparison.get('error')}")

    lines.append("")
    lines.append("---")
    lines.append("To get the full AI-powered analysis, start Ollama and "
                 "ensure a Gemma model is pulled.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section extraction from AI response (best-effort)
# ---------------------------------------------------------------------------

def _extract_section(text, heading_keyword):
    """
    Extract bullet points or numbered items from a section whose heading
    contains the given keyword (case-insensitive).

    This is a best-effort parser for the AI's free-text response.
    Returns a list of strings (one per item found).
    """
    items = []
    in_section = False

    for line in text.splitlines():
        stripped = line.strip()

        # Detect a markdown heading that contains our keyword
        if stripped.startswith("#") and heading_keyword.lower() in stripped.lower():
            in_section = True
            continue

        # A new heading means the section ended
        if stripped.startswith("#") and in_section:
            break

        # Collect list items within the section
        if in_section and (stripped.startswith("-") or stripped.startswith("*")
                           or (len(stripped) > 2 and stripped[0].isdigit()
                               and stripped[1] in ".)")):
            # Remove the bullet/number prefix
            clean = stripped.lstrip("-*0123456789.) ").strip()
            if clean:
                items.append(clean)

    return items
