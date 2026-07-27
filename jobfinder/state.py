"""Persist the set of seen job keys to a per-category JSON file."""
import json
import os


def load(path):
    """Return the set of previously-seen job keys (empty if no state yet)."""
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return set()
    return set(data.get("seen", []) if isinstance(data, dict) else data)


def save(keys, path):
    """Persist ``keys`` (an iterable of job keys) as sorted JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"seen": sorted(keys)}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
