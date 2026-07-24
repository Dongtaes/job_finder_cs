"""Keep Germany / Europe / unspecified roles and label their group."""
import re

from . import config

GROUP_GERMANY = "Germany"
GROUP_EUROPE = "Europe"
GROUP_REMOTE = "Remote/Unspecified"

_PLUS_SUFFIX_RE = re.compile(r"\+\s*\d+\s*$")
# Leading "Remote" / "EMEA" qualifier on the country segment, e.g. "Remote - France".
_REMOTE_PREFIX_RE = re.compile(r"^(remote|emea)\b[\s\-–—:]*", re.IGNORECASE)


def _country_of(location):
    """Return the lowercase country token of a location, or '' if none.

    Uses the last comma-separated segment and strips a leading Remote/EMEA
    qualifier so "Remote - France" -> "france" and "Remote - Berlin, Germany"
    -> "germany".
    """
    loc = _PLUS_SUFFIX_RE.sub("", location or "").strip()
    if not loc:
        return ""
    segment = loc.split(",")[-1].strip()
    segment = _REMOTE_PREFIX_RE.sub("", segment).strip()
    return segment.lower()


def classify(location):
    """Return a group label for ``location``, or None to drop it.

    Kept: Germany, curated Europe countries, and location-unspecified roles
    (blank, or bare "Remote"/"EMEA" with no identifiable country). A remote
    role tied to a country is judged by that country, so "Remote - Canada"
    is dropped while "Remote - France" is Europe.
    """
    loc = (location or "").strip()
    low = loc.lower()
    if not loc:
        return GROUP_REMOTE

    country = _country_of(loc)
    if country == config.GERMANY:
        return GROUP_GERMANY
    if country in config.EUROPE_COUNTRIES:
        return GROUP_EUROPE

    # No European country matched. Keep only if it's a placeless remote/EMEA role.
    is_remote = "remote" in low or "emea" in low
    if is_remote and not country:
        return GROUP_REMOTE
    return None


def filter_jobs(jobs):
    """Return the kept jobs (Germany/Europe/unspecified), each with ``.group`` set."""
    kept = []
    for job in jobs:
        group = classify(job.location)
        if group is None:
            continue
        job.group = group
        kept.append(job)
    return kept
