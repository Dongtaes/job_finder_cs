"""Download the raw markdown for each configured source."""
import requests

from . import config

TIMEOUT = 30


def fetch_source(url):
    """Return the raw markdown text at ``url`` (raises on HTTP error)."""
    resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "job-finder-cs/1.0"})
    resp.raise_for_status()
    return resp.text


def fetch_all(sources=None):
    """Fetch every source, yielding ``(source_label, markdown_text)`` tuples."""
    sources = sources or config.SOURCES
    results = []
    for label, url in sources.items():
        results.append((label, fetch_source(url)))
    return results
