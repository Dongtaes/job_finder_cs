"""Keep Germany / Europe / unspecified roles and label their group."""
import re

from . import config

GROUP_GERMANY = "Germany"
GROUP_EUROPE = "Europe"
GROUP_REMOTE = "Remote/Unspecified"

# Best group wins when a posting spans several locations.
_RANK = {GROUP_GERMANY: 3, GROUP_EUROPE: 2, GROUP_REMOTE: 1, None: 0}

_PLUS_SUFFIX_RE = re.compile(r"\+\s*\d+\s*$")
# Leading "Remote" / "EMEA" qualifier on the country segment, e.g. "Remote - France".
_REMOTE_PREFIX_RE = re.compile(r"^(remote|emea)\b[\s\-–—:]*", re.IGNORECASE)


# Trailing qualifier some boards append, e.g. "Spain (Remote)".
_PARENTHETICAL_RE = re.compile(r"\([^)]*\)")


def _segments(location):
    """Split a location into cleaned, lowercased comma-separated segments."""
    loc = _PLUS_SUFFIX_RE.sub("", location or "").strip()
    loc = _PARENTHETICAL_RE.sub(" ", loc)
    out = []
    for segment in loc.split(","):
        segment = _REMOTE_PREFIX_RE.sub("", segment.strip()).strip()
        if segment:
            out.append(segment.lower())
    return out


def _country_of(location):
    """Return the lowercase country token of a location, or '' if none.

    Uses the last comma-separated segment and strips a leading Remote/EMEA
    qualifier so "Remote - France" -> "france" and "Remote - Berlin, Germany"
    -> "germany".
    """
    segments = _segments(location)
    return segments[-1] if segments else ""


def _group_of_country(segments):
    """Group implied by any recognized country in ``segments``.

    Postings order their parts inconsistently — "Berlin, Germany" from one board,
    "Germany, Berlin" from Workday — so every segment is checked, not just the
    last. Returns (group, matched) where ``matched`` says whether a country was
    recognized at all, European or not.
    """
    if any(s == config.GERMANY for s in segments):
        return GROUP_GERMANY, True
    if any(s in config.EUROPE_COUNTRIES for s in segments):
        return GROUP_EUROPE, True
    if any(s in config.NON_EUROPE_COUNTRIES for s in segments):
        return None, True
    return None, False


def _group_of_city(segments):
    """Group implied by a bare city name, for locations that name no country."""
    if any(s in config.NON_EUROPE_REGIONS for s in segments):
        return None
    if any(s in config.GERMAN_CITIES for s in segments):
        return GROUP_GERMANY
    if any(s in config.EUROPE_CITIES for s in segments):
        return GROUP_EUROPE
    return None


def classify_one(location):
    """Group for a single location string, or None to drop it."""
    loc = (location or "").strip()
    if not loc:
        return GROUP_REMOTE

    segments = _segments(loc)
    group, matched_country = _group_of_country(segments)
    if group:
        return group
    if not matched_country:
        # No country named: fall back to well-known city names, then to treating
        # a placeless "Remote"/"EMEA" row as location-unspecified.
        group = _group_of_city(segments)
        if group:
            return group
        low = loc.lower()
        if ("remote" in low or "emea" in low) and not _country_of(loc):
            return GROUP_REMOTE
    return None


def classify(location, extra_locations=()):
    """Return a group label for ``location``, or None to drop it.

    Kept: Germany, curated Europe countries, and location-unspecified roles
    (blank, or bare "Remote"/"EMEA" with no identifiable country). A remote
    role tied to a country is judged by that country, so "Remote - Canada"
    is dropped while "Remote - France" is Europe.

    ``extra_locations`` are the locations recovered from the posting itself when
    the markdown row hid them behind a "+N" suffix. The best group across all of
    them wins, so "Vancouver, Canada +1" whose second site is Munich counts as
    Germany instead of being dropped.
    """
    groups = [classify_one(location)]
    groups += [classify_one(extra) for extra in extra_locations or ()]
    # A blank visible location only means "unspecified" when nothing else is known.
    best = max(groups, key=lambda g: _RANK[g])
    return best


def classify_job(job):
    """Group for a ``Job``, taking any resolved hidden locations into account."""
    return classify(job.location, getattr(job, "resolved_locations", ()))


def display_location(job):
    """Location text for the digest: the full list once hidden sites are known."""
    resolved = list(getattr(job, "resolved_locations", ()) or ())
    if not resolved:
        return job.location
    return " · ".join(resolved)


def filter_jobs(jobs):
    """Return the kept jobs (Germany/Europe/unspecified), each with ``.group`` set."""
    kept = []
    for job in jobs:
        group = classify_job(job)
        if group is None:
            continue
        job.group = group
        kept.append(job)
    return kept
