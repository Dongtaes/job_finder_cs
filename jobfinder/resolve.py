"""Recover the locations a "+N" suffix hides on a job's location cell.

The speedyapply markdown only prints a posting's first location followed by a
"+N" counter, so a role shown as "Vancouver, Canada +1" may really also sit in
Munich. Those extra locations exist nowhere in the markdown, so this module
re-reads the posting itself: the big applicant-tracking systems expose a JSON
endpoint, and anything else falls back to the posting's JSON-LD.

Lookups are cached on disk (keyed by apply URL) so a daily run only fetches
postings it has never resolved.
"""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from urllib.parse import urlsplit

import requests

from . import config

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; job-finder-cs/1.0)"}
# The "+3" tail that stands in for the locations the markdown omitted.
_PLUS_SUFFIX_RE = re.compile(r"\+\s*(\d+)\s*$")
# Google's careers pages render each location in its own obfuscated-class span.
_GOOGLE_LOC_RE = re.compile(r'<span class="r0wTof[^"]*">([^<]{2,80})</span>')
# Location spans further apart than this belong to different postings on the page.
_GOOGLE_GROUP_GAP = 120
_JSONLD_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL
)
# Country codes seen in JSON-LD postings, mapped to the names the filter knows.
_COUNTRY_CODES = {
    "DE": "Germany", "AT": "Austria", "CH": "Switzerland", "NL": "Netherlands",
    "BE": "Belgium", "FR": "France", "IE": "Ireland", "GB": "United Kingdom",
    "UK": "United Kingdom", "ES": "Spain", "PT": "Portugal", "IT": "Italy",
    "PL": "Poland", "SE": "Sweden", "DK": "Denmark", "NO": "Norway",
    "FI": "Finland", "CZ": "Czechia", "LU": "Luxembourg", "HU": "Hungary",
    "RO": "Romania", "GR": "Greece", "EE": "Estonia", "LT": "Lithuania",
    "LV": "Latvia", "HR": "Croatia", "SK": "Slovakia", "SI": "Slovenia",
    "BG": "Bulgaria", "IS": "Iceland", "CY": "Cyprus", "MT": "Malta",
    "US": "USA", "CA": "Canada", "IN": "India", "CN": "China", "IL": "Israel",
    "SG": "Singapore", "JP": "Japan", "AU": "Australia", "BR": "Brazil",
    "HK": "Hong Kong", "TW": "Taiwan", "KR": "South Korea", "MX": "Mexico",
    "PH": "Philippines", "ID": "Indonesia", "MY": "Malaysia", "TH": "Thailand",
    "VN": "Vietnam", "AE": "United Arab Emirates", "ZA": "South Africa",
    "TR": "Turkey", "UA": "Ukraine", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "NZ": "New Zealand", "EG": "Egypt",
    "PK": "Pakistan", "RS": "Serbia", "RU": "Russia", "CR": "Costa Rica",
}
# Placeholder some boards emit instead of a real region.
_PLACEHOLDERS = {"unavailable", "n/a", "na", "none", "-"}


def hidden_count(location):
    """Return N from a trailing "+N" on ``location`` (0 when there is none)."""
    m = _PLUS_SUFFIX_RE.search(location or "")
    return int(m.group(1)) if m else 0


def _join(*parts):
    """Join non-empty location parts into "City, Region, Country" form."""
    seen = []
    for part in parts:
        part = (part or "").strip().strip(",")
        if part.lower() in _PLACEHOLDERS:
            continue
        if part and part.lower() not in [s.lower() for s in seen]:
            seen.append(part)
    return ", ".join(seen)


def _clean(values):
    """Drop blanks and duplicates, preserving order."""
    out = []
    for value in values:
        value = re.sub(r"^\s*[;,]\s*", "", (value or "").strip())
        if value and value not in out:
            out.append(value)
    return out


def _get(url, as_json=True):
    """GET ``url``, returning parsed JSON / text, or None on any failure."""
    try:
        resp = requests.get(url, timeout=config.RESOLVE_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
        return resp.json() if as_json else resp.text
    except (requests.RequestException, ValueError):
        return None


def _ashby(url, path, hint=""):
    # jobs.ashbyhq.com/<org>/<job-id>
    parts = path.strip("/").split("/")
    if len(parts) < 2:
        return []
    board = _get(f"https://api.ashbyhq.com/posting-api/job-board/{parts[0]}")
    if not isinstance(board, dict):
        return []
    for job in board.get("jobs", []):
        if job.get("id") != parts[1] and parts[1] not in (job.get("jobUrl") or ""):
            continue
        entries = [(job.get("location"), job.get("address"))]
        entries += [
            (sec.get("location"), sec.get("address"))
            for sec in job.get("secondaryLocations") or []
        ]
        out = []
        for name, address in entries:
            country = ((address or {}).get("postalAddress") or {}).get("addressCountry")
            out.append(_join(name, country))
        return _clean(out)
    return []


def _greenhouse(url, path, hint=""):
    # (job-boards|boards)[.eu].greenhouse.io/<board>/jobs/<id>
    m = re.search(r"/([^/]+)/jobs/(\d+)", path)
    if not m:
        return []
    data = _get(f"https://api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}")
    if not isinstance(data, dict):
        return []
    names = [office.get("name") for office in data.get("offices") or []]
    names.append((data.get("location") or {}).get("name"))
    # Greenhouse packs multiple locations into one string.
    out = []
    for name in names:
        out.extend(re.split(r"\s*(?:;|\bor\b|\|)\s*", name or ""))
    return _clean(out)


def _lever(url, path, hint=""):
    # jobs.lever.co/<org>/<id>
    parts = path.strip("/").split("/")
    if len(parts) < 2:
        return []
    data = _get(f"https://api.lever.co/v0/postings/{parts[0]}/{parts[1]}")
    if not isinstance(data, dict):
        return []
    categories = data.get("categories") or {}
    return _clean(categories.get("allLocations") or [categories.get("location")])


def _workable(url, path, hint=""):
    # apply.workable.com/<account>/j/<shortcode>/
    m = re.search(r"/([^/]+)/j/([^/]+)", path)
    if not m:
        return []
    data = _get(
        f"https://apply.workable.com/api/v1/accounts/{m.group(1)}/jobs/{m.group(2)}"
    )
    if not isinstance(data, dict):
        return []
    entries = data.get("locations") or [data.get("location")]
    return _clean(
        _join(loc.get("city"), loc.get("country")) for loc in entries if loc
    )


def _workday(url, path, hint=""):
    # <tenant>.wdN.myworkdayjobs.com/[lang/]<site>/job/<rest>
    host = urlsplit(url).netloc
    tenant = host.split(".")[0]
    parts = [p for p in path.strip("/").split("/") if p]
    if "job" not in parts:
        return []
    site_index = parts.index("job") - 1
    if site_index < 0:
        return []
    tail = "/".join(parts[site_index:])
    data = _get(f"https://{host}/wday/cxs/{tenant}/{tail}")
    if not isinstance(data, dict):
        return []
    info = data.get("jobPostingInfo") or {}
    return _clean([info.get("location")] + list(info.get("additionalLocations") or []))


# Career sites that embed a Greenhouse board pass the posting id as ?gh_jid=.
_GH_JID_RE = re.compile(r"[?&]gh_jid=(\d+)")
# The board token those pages hand to the Greenhouse embed script, which appears
# either as ?for=<board> or as a path on greenhouse.io.
_GH_BOARD_RE = re.compile(r"(?:[?&]for=|greenhouse\.io/(?:embed/)?)([a-zA-Z0-9_-]+)")
# Path words on those URLs that are never a board token.
_GH_NON_BOARDS = {"embed", "job_board", "job_app", "js", "jobs", "v1", "boards"}


def _greenhouse_embed(url, path, hint=""):
    """Career page that embeds a Greenhouse board: read its board token, then API."""
    m = _GH_JID_RE.search(url)
    if not m:
        return []
    html = _get(url, as_json=False)
    if not html:
        return []
    for board in _GH_BOARD_RE.findall(html):
        if board in _GH_NON_BOARDS:
            continue
        found = _greenhouse(url, f"/{board}/jobs/{m.group(1)}")
        if found:
            return found
    return []


def _icims(url, path, hint=""):
    """iCIMS serves the real posting (with its JSON-LD) inside an iframe."""
    base = url.split("?")[0].rstrip("/")
    return _generic(f"{base}?in_iframe=1", path)


def _google(url, path, hint=""):
    """Google careers pages list the job's sites and every similar job's sites.

    The spans carry obfuscated class names and the page's own block is not first,
    so the runs of adjacent location spans are grouped and the run containing the
    location the markdown row already showed (``hint``) is the job's own.
    """
    html = _get(url, as_json=False)
    if not html:
        return []

    groups, last_end = [], None
    for match in _GOOGLE_LOC_RE.finditer(html):
        if last_end is None or match.start() - last_end > _GOOGLE_GROUP_GAP:
            groups.append([])
        groups[-1].append(match.group(1))
        last_end = match.end()

    city = _PLUS_SUFFIX_RE.sub("", hint or "").split(",")[0].strip().lower()
    for group in groups:
        if city and any(city in loc.lower() for loc in group):
            return _clean(group)
    return []


def _jsonld_locations(node):
    """Pull "City, Country" strings out of a JSON-LD jobLocation value."""
    if isinstance(node, list):
        out = []
        for item in node:
            out.extend(_jsonld_locations(item))
        return out
    if not isinstance(node, dict):
        return []
    address = node.get("address") or node
    if isinstance(address, str):
        return [address.strip()]
    if not isinstance(address, dict):
        return []
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    country = _COUNTRY_CODES.get((country or "").strip().upper(), country)
    joined = _join(
        address.get("addressLocality"), address.get("addressRegion"), country
    )
    # Some postings give only a bare Place name ("Amsterdam").
    return [joined or (node.get("name") or "").strip()]


def _generic(url, path, hint=""):
    """Last resort: read the posting's JSON-LD JobPosting block."""
    html = _get(url, as_json=False)
    if not html:
        return []
    out = []
    for blob in _JSONLD_RE.findall(html):
        try:
            data = json.loads(blob.strip())
        except ValueError:
            continue
        for node in data if isinstance(data, list) else [data]:
            if isinstance(node, dict) and node.get("jobLocation"):
                out.extend(_jsonld_locations(node["jobLocation"]))
    return _clean(out)


# Host pattern -> handler. The first match wins; _generic catches the rest.
_HANDLERS = [
    (re.compile(r"(^|\.)ashbyhq\.com$"), _ashby),
    (re.compile(r"(^|\.)greenhouse\.io$"), _greenhouse),
    (re.compile(r"(^|\.)lever\.co$"), _lever),
    (re.compile(r"(^|\.)workable\.com$"), _workable),
    (re.compile(r"(^|\.)myworkdayjobs\.com$"), _workday),
    (re.compile(r"(^|\.)google\.com$"), _google),
    (re.compile(r"(^|\.)icims\.com$"), _icims),
]


def resolve(url, hint=""):
    """Return every location listed on the posting at ``url`` (empty on failure).

    ``hint`` is the location the markdown row displayed; pages that list several
    postings use it to pick out the one being resolved.
    """
    if not url:
        return []
    split = urlsplit(url)
    host, path = split.netloc.lower(), split.path
    for pattern, handler in _HANDLERS:
        if pattern.search(host):
            try:
                found = handler(url, path, hint)
            except Exception:  # a malformed posting must not kill the run
                found = []
            if found:
                return found
            break
    for fallback in (_greenhouse_embed, _generic):
        try:
            found = fallback(url, path, hint)
        except Exception:
            found = []
        if found:
            return found
    return []


def load_cache(path):
    """Return the cached ``{url: {"locations": [...], "fetched": "YYYY-MM-DD"}}``."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return {}
    return data.get("locations", {}) if isinstance(data, dict) else {}


def save_cache(cache, path):
    """Persist ``cache`` as sorted JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"locations": dict(sorted(cache.items()))}, fh, indent=2,
                  ensure_ascii=False)
        fh.write("\n")


def _is_fresh(entry, today):
    """Whether a cache entry is still usable (failures expire sooner)."""
    if not isinstance(entry, dict):
        return False
    try:
        fetched = date.fromisoformat(entry.get("fetched", ""))
    except ValueError:
        return False
    days = (
        config.LOCATION_TTL_DAYS
        if entry.get("locations")
        else config.LOCATION_FAILURE_TTL_DAYS
    )
    return today - fetched <= timedelta(days=days)


def resolve_jobs(jobs, cache_path, resolver=resolve, today=None):
    """Fill in ``job.resolved_locations`` for every job whose row hides locations.

    Only jobs with a "+N" suffix are looked up, and only those missing a fresh
    cache entry hit the network. The cache is rewritten with just the URLs seen
    on this run, so it self-prunes as postings expire.
    """
    today = today or date.today()
    cache = load_cache(cache_path)
    pending = {}
    for job in jobs:
        if not hidden_count(job.location) or not job.apply_url:
            continue
        entry = cache.get(job.apply_url)
        if _is_fresh(entry, today):
            job.resolved_locations = list(entry.get("locations") or [])
        else:
            pending.setdefault(job.apply_url, []).append(job)

    if pending:
        hints = [group[0].location for group in pending.values()]
        with ThreadPoolExecutor(max_workers=config.RESOLVE_WORKERS) as pool:
            results = dict(zip(pending, pool.map(resolver, pending, hints)))
        for url, group in pending.items():
            found = results.get(url) or []
            cache[url] = {"locations": found, "fetched": today.isoformat()}
            for job in group:
                job.resolved_locations = list(found)

    live = {job.apply_url for job in jobs if hidden_count(job.location) and job.apply_url}
    save_cache({url: entry for url, entry in cache.items() if url in live}, cache_path)
    return sum(1 for job in jobs if job.resolved_locations)
