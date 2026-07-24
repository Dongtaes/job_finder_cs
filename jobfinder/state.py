"""Persist the set of seen job keys to data/seen.json."""
import json
import os

from . import config


def load(path=None):
    """Return the set of previously-seen job keys (empty if no state yet)."""
    path = path or config.STATE_PATH
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return set()
    return set(data.get("seen", []) if isinstance(data, dict) else data)


def save(keys, path=None):
    """Persist ``keys`` (an iterable of job keys) as sorted JSON."""
    path = path or config.STATE_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"seen": sorted(keys)}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
