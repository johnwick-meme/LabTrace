"""
LabTrace — lightweight student-facing Streamlit app.

Integration rule:
- This file owns only the interface and integration adapters.
- It does not replace core/calculations.py, core/memory.py, or harness/agent.py.
- Until teammate interfaces are confirmed, the app runs in clearly-labelled DEMO MOCK mode.
"""
from __future__ import annotations

import json
import inspect
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UI_MEMORY_FILE = DATA_DIR / "labtrace_ui_memory.json"
SAMPLE_FILE = DATA_DIR / "sample_experiment.json"

ILLUSTRATIVE_READINGS = [
    {"voltage_v": 2.0, "current_a": 0.02},
    {"voltage_v": 4.0, "current_a": 0.04},
    {"voltage_v": 6.0, "current_a": 0.06},
    {"voltage_v": 8.0, "current_a": 0.04},
]
DEFAULT_OBSERVATIONS = (
    "Illustrative demo data only — these are not real laboratory measurements. "
    "The first three readings follow a similar V/I pattern; the final reading differs."
)
DEFAULT_MANUAL = (
    "Ohm's law states that, for a conductor under constant physical conditions, "
    "potential difference V is proportional to current I. The ratio V/I is the "
    "resistance R. Record voltage and current, calculate resistance for each trial, "
    "and investigate readings that do not follow the observed pattern."
)

st.set_page_config(page_title="LabTrace | Experiment Investigator", page_icon="🧪", layout="wide")

# Small, restrained styling: no dashboard overload.
st.markdown("""
<style>
    .block-container {max-width: 1180px; padding-top: 1.6rem; padding-bottom: 3rem;}
    .hero {padding: 1.25rem 1.4rem; border: 1px solid rgba(128,128,128,.25);
           border-radius: 16px; margin-bottom: 1rem;}
    .muted {opacity: .72; font-size: .92rem;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.2);
           border-radius: 12px; padding: .8rem;}
    .tag {display:inline-block; border:1px solid rgba(128,128,128,.35);
          border-radius:999px; padding:.18rem .6rem; font-size:.8rem; margin-right:.3rem;}
</style>
""", unsafe_allow_html=True)


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _write_json(path: Path, value: Any) -> None:
    _ensure_data_dir()
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_sample() -> dict:
    """Load Person 2's sample file when present; otherwise use clearly-labelled demo data."""
    sample = _read_json(SAMPLE_FILE)
    if isinstance(sample, dict):
        readings = sample.get("readings") or sample.get("measurements")
        if isinstance(readings, list) and readings:
            return {
                "title": sample.get("title", sample.get("experiment_name", "Ohm's law verification")),
                "readings": _normalise_readings(readings),
                "observations": sample.get("observations", DEFAULT_OBSERVATIONS),
                "manual_text": sample.get("manual_text", sample.get("lab_manual", DEFAULT_MANUAL)),
                "source": "data/sample_experiment.json",
            }
    return {
        "title": "Ohm's law verification",
        "readings": [dict(x) for x in ILLUSTRATIVE_READINGS],
        "observations": DEFAULT_OBSERVATIONS,
        "manual_text": DEFAULT_MANUAL,
        "source": "built-in illustrative demo data (not real measurements)",
    }


def _normalise_readings(readings: list) -> list[dict]:
    result = []
    for item in readings:
        if not isinstance(item, dict):
            continue
        v = item.get("voltage_v", item.get("voltage", item.get("V")))
        i = item.get("current_a", item.get("current", item.get("I")))
        try:
            result.append({"voltage_v": float(v), "current_a": float(i)})
        except (TypeError, ValueError):
            continue
    return result


def _load_memory() -> dict | None:
    saved = _read_json(UI_MEMORY_FILE)
    return saved if isinstance(saved, dict) else None


def _save_memory(experiment: dict) -> None:
    """UI-level persistence for the demo. Replace with Person 2 memory adapter at integration."""
    _write_json(UI_MEMORY_FILE, {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "experiment": experiment,
    })


def _call_compatible(fn, payload: dict):
    """Try common single-payload calling conventions without changing teammate APIs."""
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
        return fn(**payload)
    if len(params) == 1:
        return fn(payload)
    kwargs = {k: v for k, v in payload.items() if k in sig.parameters}
    required = [p for p in params if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)]
    if all(p.name in kwargs for p in required):
        return fn(**kwargs)
    raise TypeError(f"Cannot map integration payload to {fn.__module__}.{fn.__name__}{sig}")


def run_calculation_adapter(experiment: dict) -> tuple[dict | None, str]:
    """
    Integration seam for Person 2.
    Proposed contract: core.calculations exposes calculate_experiment(payload) -> dict.
    If the team has agreed a different name/schema, change this adapter only.
    """
    try:
        import core.calculations as calculations
        fn = getattr(calculations, "calculate_experiment", None)
        if callable(fn):
            result = _call_compatible(fn, {"experiment": experiment, **experiment})
            if isinstance(result, dict):
                return result, "team calculation engine"
        return None, "calculation adapter not connected (expected calculate_experiment)"
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        return None, f"calculation engine unavailable: {exc}"


def run_agent_adapter(experiment: dict, calculations: dict | None) -> tuple[dict | None, str]:
    """
    Integration seam for Person 1.
    Proposed contract: harness.agent exposes investigate(payload) -> dict.
    Do not change the teammate's API to match this assumption; adapt this function.
    """
    # Adapt UI schema to P1 harness schema without touching P1's code
    adapted_exp = dict(experiment)
    adapted_exp.setdefault("experiment_id", adapted_exp.get("id", "exp-001"))
    adapted_exp.setdefault("name", adapted_exp.get("title", "Ohm's Law Verification"))
    # Ensure readings have 'voltage' and 'current' keys
    if "readings" in adapted_exp and isinstance(adapted_exp["readings"], list):
        adapted_readings = []
        for r in adapted_exp["readings"]:
            if isinstance(r, dict):
                adapted_readings.append({
                    "voltage": r.get("voltage", r.get("voltage_v", r.get("V"))),
                    "current": r.get("current", r.get("current_a", r.get("I"))),
                    **r
                })
        adapted_exp["readings"] = adapted_readings

    payload = {"experiment": adapted_exp, "calculations": calculations}
    try:
        import harness.agent as agent
        for name in ("investigate", "run_investigation", "run_agent"):
            fn = getattr(agent, name, None)
            if callable(fn):
                result = _call_compatible(fn, {**payload, **adapted_exp})
                if isinstance(result, dict):
                    return result, f"harness.agent.{name}"
        return None, "agent adapter not connected (expected investigate/run_investigation/run_agent)"
    except (ImportError, AttributeError, TypeError, ValueError) as exc:
        return None, f"agent unavailable: {exc}"


def run_memory_save_adapter(experiment: dict) -> str:
    """Best-effort adapter for Person 2 memory; UI JSON persistence remains the fallback."""
    try:
        import core.memory as memory
        for name in ("save_experiment", "save", "store_experiment"):
            fn = getattr(memory, name, None)
            if callable(fn):
                _call_compatible(fn, {"experiment": experiment, **experiment})
                return f"core.memory.{name}"
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    return "UI JSON memory fallback"


def _mock_investigation(experiment: dict) -> dict:
    """
    Temporary deterministic UI mock. This is not Gemma output and not the team's
    calculation engine. It only makes the interaction flow demonstrable before integration.
    """
    rows = []
    for idx, point in enumerate(experiment["readings"], start=1):
        v, current = point["voltage_v"], point["current_a"]
        resistance = (v / current) if current != 0 else None
        rows.append({
            "trial": idx, "voltage_v": v, "current_a": current,
            "resistance_ohm": resistance,
            "status": "cannot calculate (current is zero)" if resistance is None else "mock calculation",
        })
    valid = [r["resistance_ohm"] for r in rows if r["resistance_ohm"] is not None]
    baseline = valid[:3]
    baseline_avg = sum(baseline) / len(baseline) if baseline else None
    flagged = []
    if baseline_avg is not None and len(rows) >= 4 and rows[3]["resistance_ohm"] is not None:
        final_r = rows[3]["resistance_ohm"]
        # Transparent demo rule, explicitly labelled as a UI mock rather than AI reasoning.
        if abs(final_r - baseline_avg) / max(abs(baseline_avg), 1e-9) > 0.2:
            flagged.append({
                "title": "Final reading differs from the earlier pattern",
                "detail": f"Trial 4 gives {final_r:.1f} Ω; trials 1–3 average {baseline_avg:.1f} Ω. "
                          "This is a pattern-based flag, not proof that the reading is wrong.",
                "type": "calculated comparison",
            })
    return {
        "calculations": {"rows": rows, "baseline_mean_ohm": baseline_avg},
        "anomalies": flagged,
        "explanations": [
            {"kind": "hypothesis", "text": "Check whether the ammeter reading, connections, or instrument range were recorded correctly."},
            {"kind": "hypothesis", "text": "Consider whether the conductor's temperature or contact resistance changed between trials."},
        ] if flagged else [],
        "evidence": [
            {"source": "User-entered readings", "passage": "The four voltage/current pairs entered in the Experiment view."},
            {"source": "Lab manual text", "passage": experiment.get("manual_text", "")[:500]},
        ],
        "trace": [
            {"stage": "Input validation", "result": f"Received {len(experiment['readings'])} reading(s)."},
            {"stage": "Calculation", "result": "DEMO MOCK: transparent V/I calculation for interface preview."},
            {"stage": "Pattern check", "result": f"{len(flagged)} pattern flag(s) generated by the UI mock."},
            {"stage": "Evidence assembly", "result": "Showing entered readings and the supplied lab-manual passage."},
        ],
        "mode": "DEMO MOCK — not produced by Gemma",
    }


def _extract_investigation(agent_result: dict | None, calculation_result: dict | None,
                           experiment: dict) -> dict:
    """Normalise only the UI-facing shape; preserve raw result for inspection."""
    if agent_result is None and calculation_result is None:
        return _mock_investigation(experiment)
    result = dict(agent_result or {})
    if calculation_result is not None and "calculations" not in result:
        result["calculations"] = calculation_result
    result.setdefault("anomalies", result.get("flags", []))
    result.setdefault("explanations", [])
    result.setdefault("evidence", [])
    result.setdefault("trace", [])
    result["mode"] = "CONNECTED TEAM COMPONENTS (verify which components ran)"
    result["_raw_agent_result"] = agent_result
    result["_raw_calculation_result"] = calculation_result
    return result


def _safe_float(value: Any, field: str, row_number: int) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Trial {row_number}: enter a valid number for {field}.")
    if parsed < 0:
        raise ValueError(f"Trial {row_number}: {field} cannot be negative for this demo.")
    return parsed


def _render_readings_table(readings: list[dict]) -> None:
    st.dataframe(
        [{"Trial": i, "Voltage (V)": r["voltage_v"], "Current (A)": r["current_a"]}
         for i, r in enumerate(readings, 1)],
        use_container_width=True, hide_index=True
    )


def _render_calculations(calculations: Any, original_readings: list[dict]) -> None:
    st.markdown("#### Original readings")
    _render_readings_table(original_readings)
    st.markdown("#### Calculated results")
    rows = None
    if isinstance(calculations, dict):
        rows = calculations.get("rows") or calculations.get("results") or calculations.get("trials")
        if rows is None and isinstance(calculations.get("per_reading"), list):
            rows = calculations["per_reading"]
    if isinstance(rows, list) and rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    elif isinstance(calculations, dict):
        st.json(calculations, expanded=True)
    elif calculations is not None:
        st.write(calculations)
    else:
        st.info("No calculation result was returned. Connect Person 2's calculation adapter.")


def _render_items(items: Any, empty_text: str, kind: str = "item") -> None:
    if not isinstance(items, list) or not items:
        st.info(empty_text)
        return
    for index, item in enumerate(items, 1):
        if isinstance(item, dict):
            title = item.get("title", item.get("name", f"{kind.title()} {index}"))
            body = item.get("detail", item.get("text", item.get("passage", "")))
            label = item.get("type", item.get("kind", item.get("source", "")))
        else:
            title, body, label = f"{kind.title()} {index}", str(item), ""
        with st.container(border=True):
            if label:
                st.caption(str(label))
            st.markdown(f"**{title}**")
            st.write(body or "No details supplied.")


def _make_viva_questions(investigation: dict) -> list[dict]:
    questions = investigation.get("viva_questions")
    if isinstance(questions, list) and questions:
        normalised = []
        for q in questions:
            if isinstance(q, dict):
                normalised.append({"question": q.get("question", q.get("text", str(q))),
                                   "expected_points": q.get("expected_points", q.get("rubric", [])),
                                   "source": q.get("source", "Agent response")})
            else:
                normalised.append({"question": str(q), "expected_points": [], "source": "Agent response"})
        return normalised
    return [
        {"question": "Using your saved readings, calculate the resistance for Trial 2 and explain what the value represents.",
         "expected_points": ["R = V/I", "4 V / 0.04 A = 100 Ω", "resistance is the ratio of voltage to current"],
         "source": "Generated fallback question from saved readings; not Gemma output"},
        {"question": "Why should Trial 4 be investigated rather than immediately discarded?",
         "expected_points": ["it differs from the earlier pattern", "a flag is not proof of error", "check setup and repeat measurement"],
         "source": "Generated fallback question from the visible pattern; not Gemma output"},
    ]


def _feedback(answer: str, expected_points: list) -> tuple[str, list[str]]:
    """Evidence-aware lightweight feedback for fallback viva only; no claim of AI grading."""
    if not answer.strip():
        return "Enter an answer to receive feedback.", []
    lowered = answer.lower()
    found = []
    for point in expected_points:
        tokens = [t.strip(".,:;()") for t in str(point).lower().split() if len(t.strip(".,:;()")) > 2]
        if tokens and any(token in lowered for token in tokens):
            found.append(str(point))
    if expected_points:
        return ("Fallback keyword check only — not an AI assessment. Compare your answer with the points below.",
                found)
    return ("Answer saved. No scoring rubric was provided by the connected agent.", found)


def main() -> None:
    st.markdown('<div class="hero"><h1>🧪 LabTrace</h1><p>Investigate an experiment. Preserve the evidence. Prepare for your viva.</p><span class="tag">Local-first</span><span class="tag">Ohm’s law MVP</span><span class="tag">Inspectable workflow</span></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### LabTrace")
        st.caption("Student experiment workspace")
        view = st.radio("Go to", ["Experiment", "Investigation", "Viva"], label_visibility="collapsed")
        st.divider()
        st.caption("Demo status")
        st.info("Illustrative data only. Mock output is labelled and never presented as Gemma output.")
        if st.button("Reload saved experiment", use_container_width=True):
            saved = _load_memory()
            if saved and isinstance(saved.get("experiment"), dict):
                st.session_state["experiment_data"] = saved["experiment"]
                st.session_state["saved_at"] = saved.get("saved_at")
                st.session_state["investigation_result"] = None
                st.success("Loaded the saved UI experiment.")
            else:
                st.warning("No saved experiment found yet.")

    if "experiment_data" not in st.session_state:
        st.session_state["experiment_data"] = _load_sample()
    if "investigation_result" not in st.session_state:
        st.session_state["investigation_result"] = None
    if "viva_answers" not in st.session_state:
        st.session_state["viva_answers"] = {}

    if view == "Experiment":
        st.subheader("1 · Experiment")
        st.write("Enter readings or load the illustrative example. The sample values are **not real measurements**.")
        left, right = st.columns([1.1, 1])
        with left:
            title = st.text_input("Experiment name", value=st.session_state["experiment_data"].get("title", "Ohm's law verification"))
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Load illustrative readings", use_container_width=True):
                    st.session_state["experiment_data"] = {
                        "title": "Ohm's law verification",
                        "readings": [dict(x) for x in ILLUSTRATIVE_READINGS],
                        "observations": DEFAULT_OBSERVATIONS,
                        "manual_text": DEFAULT_MANUAL,
                        "source": "illustrative demo data (not real measurements)",
                    }
                    st.session_state["investigation_result"] = None
                    st.rerun()
            with c2:
                if st.button("Load last saved experiment", use_container_width=True):
                    saved = _load_memory()
                    if saved and isinstance(saved.get("experiment"), dict):
                        st.session_state["experiment_data"] = saved["experiment"]
                        st.session_state["investigation_result"] = None
                        st.rerun()
                    else:
                        st.warning("Nothing has been saved yet.")
            current_readings = st.session_state["experiment_data"].get("readings", ILLUSTRATIVE_READINGS)
            count = st.number_input("Number of trials", min_value=1, max_value=12,
                                    value=max(1, min(12, len(current_readings))), step=1)
            readings = []
            for idx in range(int(count)):
                initial = current_readings[idx] if idx < len(current_readings) else {"voltage_v": 0.0, "current_a": 0.0}
                st.markdown(f"**Trial {idx + 1}**")
                a, b = st.columns(2)
                with a:
                    voltage = st.number_input(f"Voltage (V) · Trial {idx + 1}", min_value=0.0,
                        value=float(initial.get("voltage_v", 0.0)), step=0.5, format="%.3f", key=f"v_{idx}")
                with b:
                    current = st.number_input(f"Current (A) · Trial {idx + 1}", min_value=0.0,
                        value=float(initial.get("current_a", 0.0)), step=0.01, format="%.4f", key=f"i_{idx}")
                readings.append({"voltage_v": voltage, "current_a": current})
        with right:
            observations = st.text_area("Observations / notes", value=st.session_state["experiment_data"].get("observations", DEFAULT_OBSERVATIONS), height=160)
            manual_text = st.text_area("Lab-manual text / reference passage", value=st.session_state["experiment_data"].get("manual_text", DEFAULT_MANUAL), height=260)
            st.caption("Evidence is strongest when the relevant manual passage and original readings are preserved.")
        if st.button("Save experiment", type="primary", use_container_width=True):
            experiment = {"title": title.strip() or "Untitled experiment", "readings": readings,
                          "observations": observations, "manual_text": manual_text,
                          "saved_from": "Experiment view"}
            if not readings:
                st.error("Add at least one reading before saving.")
            else:
                st.session_state["experiment_data"] = experiment
                _save_memory(experiment)
                memory_source = run_memory_save_adapter(experiment)
                st.session_state["saved_at"] = datetime.now().isoformat(timespec="seconds")
                st.success(f"Experiment saved locally. Persistence: {memory_source}.")
        st.caption(f"Current sample source: {st.session_state['experiment_data'].get('source', 'entered by user')}")

    elif view == "Investigation":
        st.subheader("2 · Investigation")
        st.write("Run the investigation to see calculations, possible inconsistencies, evidence, and a readable activity trace.")
        experiment = st.session_state["experiment_data"]
        if not experiment.get("readings"):
            st.warning("No readings are available. Add or load readings in Experiment first.")
        else:
            st.markdown(f"**Experiment:** {experiment.get('title', 'Untitled experiment')}")
            _render_readings_table(experiment["readings"])
            if st.button("Run investigation", type="primary", use_container_width=True):
                with st.spinner("Validating inputs and running available components…"):
                    calc_result, calc_status = run_calculation_adapter(experiment)
                    agent_result, agent_status = run_agent_adapter(experiment, calc_result)
                    result = _extract_investigation(agent_result, calc_result, experiment)
                    if agent_result is None and calc_result is None:
                        result["trace"].insert(0, {"stage": "Integration status",
                            "result": f"{calc_status}; {agent_status}. Using clearly labelled UI mock."})
                    else:
                        result["trace"].insert(0, {"stage": "Integration status",
                            "result": f"Calculations: {calc_status}; Agent: {agent_status}."})
                    _save_memory(experiment)
                    st.session_state["investigation_result"] = result
                    st.session_state["investigation_ran_at"] = datetime.now().isoformat(timespec="seconds")
            result = st.session_state.get("investigation_result")
            if result:
                st.warning(result.get("mode", "Connected result — inspect trace to verify which components ran."))
                calc = result.get("calculations")
                _render_calculations(calc, experiment["readings"])
                st.markdown("#### Flagged anomalies")
                _render_items(result.get("anomalies"), "No anomalies were returned. This does not prove every reading is correct.", "anomaly")
                st.markdown("#### Explanations and hypotheses")
                _render_items(result.get("explanations"), "No explanations were returned by the connected components.", "explanation")
                st.markdown("#### Evidence and source passages")
                _render_items(result.get("evidence"), "No evidence objects were returned. Check the raw result and adapter schema.", "evidence")
                st.markdown("#### Activity trace")
                trace = result.get("trace")
                if isinstance(trace, list) and trace:
                    for entry in trace:
                        if isinstance(entry, dict):
                            stage_label = entry.get("stage") or entry.get("step") or "Stage"
                            detail_label = entry.get("result") or entry.get("detail") or entry.get("error") or "No result supplied."
                            st.markdown(f"- **{stage_label}** — {detail_label}")
                        else:
                            st.markdown(f"- {entry}")
                else:
                    st.info("No structured trace was returned by the harness.")
                with st.expander("Inspect raw connected result"):
                    st.json({k: v for k, v in result.items() if not k.startswith("_")}, expanded=False)

    else:
        st.subheader("3 · Viva")
        experiment = st.session_state["experiment_data"]
        result = st.session_state.get("investigation_result")
        if not experiment.get("readings"):
            st.warning("Add or load an experiment first.")
        else:
            if result is None:
                st.info("Run an investigation first. Viva questions will use the saved readings and connected agent output when available.")
            questions = _make_viva_questions(result or {})
            if "viva_index" not in st.session_state:
                st.session_state["viva_index"] = 0
            index = min(st.session_state["viva_index"], len(questions) - 1)
            q = questions[index]
            st.caption(f"Question {index + 1} of {len(questions)} · Source: {q.get('source', 'not specified')}")
            st.markdown(f"### {q['question']}")
            answer_key = f"answer_{index}"
            answer = st.text_area("Your answer", value=st.session_state["viva_answers"].get(index, ""),
                                  height=160, key=answer_key,
                                  placeholder="Explain your reasoning and refer to the readings or lab-manual evidence.")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("Save answer & get feedback", type="primary", use_container_width=True):
                    st.session_state["viva_answers"][index] = answer
                    feedback, found = _feedback(answer, q.get("expected_points", []))
                    st.session_state[f"feedback_{index}"] = {"text": feedback, "found": found}
            with c2:
                if st.button("Next question", use_container_width=True, disabled=index >= len(questions) - 1):
                    st.session_state["viva_index"] = index + 1
                    st.rerun()
            feedback = st.session_state.get(f"feedback_{index}")
            if feedback:
                st.markdown("#### Feedback")
                st.write(feedback["text"])
                if feedback["found"]:
                    st.markdown("Points detected by fallback keyword check:")
                    for point in feedback["found"]:
                        st.markdown(f"- {point}")
                elif q.get("expected_points"):
                    st.caption("No rubric keywords detected. This does not necessarily mean the answer is incorrect.")
                with st.expander("Reference points (for self-review)"):
                    st.write(q.get("expected_points") or "No rubric supplied by the agent.")
            st.caption("Fallback viva feedback is a simple keyword check, not Gemma evaluation. A connected harness should return its own evidence-grounded feedback.")

    st.divider()
    st.caption("LabTrace · Local demo · Preserve original readings · Distinguish observations from hypotheses")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        st.error("LabTrace encountered an unexpected error. Your inputs should remain available in the current session.")
        st.exception(exc)
