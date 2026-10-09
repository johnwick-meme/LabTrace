"""
core/memory.py — Local experiment persistence.

Owned by: Programmer 2.

Saves and loads experiment records as JSON files in a dedicated data directory.
No external services, no cloud storage.

Public API (agreed function contract):
    save_experiment(experiment)         -> str   (path of the saved file)
    load_experiment(experiment_id)      -> dict | None
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Storage location
# ---------------------------------------------------------------------------

# Resolved relative to this file: LabTrace_UI_Starter/data/experiments/
_MODULE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _MODULE_DIR.parent
EXPERIMENTS_DIR = _PROJECT_ROOT / "data" / "experiments"


def _ensure_dir() -> None:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _experiment_path(experiment_id: str) -> Path:
    return EXPERIMENTS_DIR / f"{experiment_id}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_experiment(experiment: dict) -> str:
    """
    Persist an experiment record to disk.

    If ``experiment`` already contains an ``id`` key, that value is used as
    the filename stem so that repeated saves overwrite the same record.
    Otherwise a UUID4 is assigned and stored inside the experiment dict.

    Parameters
    ----------
    experiment : dict
        Experiment data, including at minimum a ``readings`` list.

    Returns
    -------
    str
        Absolute path of the saved file.

    Raises
    ------
    TypeError  if experiment is not a dict.
    ValueError if the experiment contains no readings.
    """
    if not isinstance(experiment, dict):
        raise TypeError(
            f"save_experiment: expected a dict, got {type(experiment).__name__!r}."
        )

    readings = experiment.get("readings") or experiment.get("measurements") or []
    if not isinstance(readings, list) or not readings:
        raise ValueError(
            "save_experiment: experiment must contain a non-empty 'readings' list."
        )

    _ensure_dir()

    # Assign or reuse an ID
    experiment_id = str(experiment.get("experiment_id") or experiment.get("id") or uuid.uuid4())
    record = {
        **experiment,
        "experiment_id": experiment_id,
        "id": experiment_id,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }

    path = _experiment_path(experiment_id)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return experiment_id


def load_experiment(experiment_id: str) -> dict | None:
    """
    Load a previously saved experiment by its ID.

    Parameters
    ----------
    experiment_id : str
        The UUID or identifier returned by save_experiment.

    Returns
    -------
    dict
        The experiment record, or ``None`` if not found or unreadable.

    Raises
    ------
    TypeError  if experiment_id is not a string.
    """
    if not isinstance(experiment_id, str):
        raise TypeError(
            f"load_experiment: experiment_id must be a str, got {type(experiment_id).__name__!r}."
        )

    path = _experiment_path(experiment_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def search_manual(query: str, manual_text: str) -> list[str]:
    """
    Search the manual/reference text for lines matching a query.

    Parameters
    ----------
    query : str
        The search term.
    manual_text : str
        The full text of the manual/reference.

    Returns
    -------
    list[str]
        Lines from manual_text that contain the query keywords.
    """
    if not query or not manual_text:
        return []
    query_lower = query.lower()
    return [
        line.strip()
        for line in manual_text.splitlines()
        if query_lower in line.lower()
    ]


def list_experiments() -> list[dict]:
    """
    Return a summary list of all saved experiments.

    Each entry contains ``id``, ``title``, and ``saved_at``.
    Records that cannot be parsed are silently skipped.
    """
    _ensure_dir()
    summaries = []
    for path in sorted(EXPERIMENTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                summaries.append({
                    "id": data.get("id", path.stem),
                    "title": data.get("title", "Untitled"),
                    "saved_at": data.get("saved_at", ""),
                })
        except (OSError, json.JSONDecodeError):
            continue
    return summaries

