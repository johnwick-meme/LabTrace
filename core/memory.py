"""
core/memory.py — STUB (Programmer 2's responsibility)

Placeholder implementations for experiment persistence.
Will be replaced by Programmer 2's real storage code.

Agreed signatures:
    save_experiment(experiment) -> str   (returns experiment_id)
    load_experiment(experiment_id) -> dict
    search_manual(query, manual_text) -> list[str]
"""

# In-memory store for the stub.  Programmer 2 will replace this with
# file-based or database storage.
_store = {}


def save_experiment(experiment):
    """
    Persist an experiment record.

    Parameters:
        experiment (dict): Must contain at least "experiment_id".

    Returns:
        str: The experiment_id.
    """
    exp_id = experiment.get("experiment_id")
    if not exp_id:
        raise ValueError("experiment must have an 'experiment_id' field.")
    _store[exp_id] = experiment
    return exp_id


def load_experiment(experiment_id):
    """
    Retrieve a previously saved experiment.

    Returns:
        dict: The experiment record, or None if not found.
    """
    return _store.get(experiment_id)


def search_manual(query, manual_text):
    """
    Search the manual/reference text for lines matching a query.

    This stub does simple case-insensitive substring matching.
    Programmer 2 may replace this with a smarter search.

    Parameters:
        query (str): The search term.
        manual_text (str): The full text of the manual/reference.

    Returns:
        list[str]: Lines from manual_text that contain the query.
    """
    if not query or not manual_text:
        return []
    query_lower = query.lower()
    return [
        line.strip()
        for line in manual_text.splitlines()
        if query_lower in line.lower()
    ]
