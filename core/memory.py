
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from copy import deepcopy


# Store experiment files inside the project's data folder.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_experiment(experiment):
    """Save an experiment as JSON without modifying the supplied dictionary."""
    if not isinstance(experiment, dict):
        raise ValueError("Experiment must be a dictionary.")

    experiment_id = experiment.get("experiment_id")

    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("A non-empty experiment_id is required.")

    # Prevent IDs from creating files outside the data directory.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", experiment_id):
        raise ValueError("Experiment ID may contain only letters, numbers, _ and -.")

    saved_data = deepcopy(experiment)
    saved_data.setdefault(
        "updated_at",
        datetime.now(timezone.utc).isoformat()
    )

    file_path = DATA_DIR / f"{experiment_id}.json"
    temporary_path = DATA_DIR / f"{experiment_id}.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(saved_data, file, indent=2, ensure_ascii=False, allow_nan=False)
            file.write("\n")

        temporary_path.replace(file_path)

    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return {
        "experiment_id": experiment_id,
        "saved": True,
        "file": str(file_path),
    }


def load_experiment(experiment_id):
    """Load an experiment by ID. Return None if it does not exist."""
    if not isinstance(experiment_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_-]+", experiment_id
    ):
        raise ValueError("Invalid experiment ID.")

    file_path = DATA_DIR / f"{experiment_id}.json"

    if not file_path.exists():
        return None

    with file_path.open("r", encoding="utf-8") as file:
        experiment = json.load(file)

    if not isinstance(experiment, dict):
        raise ValueError("Saved experiment must contain a JSON object.")

    if experiment.get("experiment_id") != experiment_id:
        raise ValueError("Saved experiment ID does not match the requested ID.")

    return experiment


def search_manual(query, manual_text):
    """Return actual matching passages from supplied manual text."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if not isinstance(manual_text, str):
        raise ValueError("Manual text must be a string.")

    terms = query.lower().split()
    passages = re.split(r"(?<=[.!?])\s+|\n+", manual_text.strip())

    results = []
    position = 0

    for passage in passages:
        start = manual_text.find(passage, position)

        if start == -1:
            continue

        end = start + len(passage)
        position = end

        passage_lower = passage.lower()
        matches = sum(term in passage_lower for term in terms)

        if matches:
            results.append({
                "text": passage,
                "start_char": start,
                "end_char": end,
                "matched_terms": matches,
            })

    results.sort(key=lambda item: item["matched_terms"], reverse=True)

    return results
