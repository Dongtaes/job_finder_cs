"""Parse the speedyapply markdown job tables into ``Job`` objects."""
import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class Job:
    company: str
    company_url: str
    position: str
    location: str
    apply_url: str
    age: str
    source: str
    group: str = field(default="")

    def key(self):
        """Stable dedup key: the apply URL, else a hash of the identifying fields."""
        if self.apply_url:
            return self.apply_url
        digest = hashlib.sha1(
            f"{self.company}|{self.position}|{self.location}".encode("utf-8")
        ).hexdigest()
        return f"sha1:{digest}"


# First href in a cell.
_HREF_RE = re.compile(r'href="([^"]+)"')
# Company name inside <strong>...</strong> (HTML form) or **...** (markdown form).
_STRONG_RE = re.compile(r"<strong>(.*?)</strong>", re.DOTALL)
_MD_LINK_RE = re.compile(r"\[\**(.*?)\**\]\((.*?)\)")
_TAG_RE = re.compile(r"<[^>]+>")
# Sub-row marker used when several postings share one company.
_CONTINUATION = {"", "↳", "&darr;", "»"}


def _strip_tags(text):
    return _TAG_RE.sub("", text).replace("&nbsp;", " ").strip()


def _first_href(cell):
    m = _HREF_RE.search(cell)
    if m:
        return m.group(1).strip()
    m = _MD_LINK_RE.search(cell)
    if m:
        return m.group(2).strip()
    return ""


def _company_name(cell):
    m = _STRONG_RE.search(cell)
    if m:
        return _strip_tags(m.group(1))
    m = _MD_LINK_RE.search(cell)
    if m:
        return m.group(1).strip()
    return _strip_tags(cell)


def _split_row(line):
    """Split a markdown table row into its cell strings, or None if not a row."""
    line = line.strip()
    if not line.startswith("|"):
        return None
    # Drop the leading/trailing pipe, then split.
    inner = line.strip().strip("|")
    return [c.strip() for c in inner.split("|")]


def _is_separator(cells):
    return all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells)


def _is_header(cells):
    lowered = [c.lower() for c in cells]
    return "company" in lowered and "position" in lowered and "location" in lowered


def parse_table(markdown, source):
    """Parse all job rows from one source's markdown into ``Job`` objects."""
    jobs = []
    last_company = ""
    last_company_url = ""
    for line in markdown.splitlines():
        cells = _split_row(line)
        if not cells or len(cells) < 5:
            continue
        if _is_separator(cells) or _is_header(cells):
            continue

        company_cell, position_cell, location_cell, posting_cell, age_cell = cells[:5]

        company_raw = _strip_tags(company_cell)
        if company_raw in _CONTINUATION:
            company = last_company
            company_url = last_company_url
        else:
            company = _company_name(company_cell)
            company_url = _first_href(company_cell)
            last_company = company
            last_company_url = company_url

        job = Job(
            company=company,
            company_url=company_url,
            position=_strip_tags(position_cell),
            location=_strip_tags(location_cell),
            apply_url=_first_href(posting_cell),
            age=_strip_tags(age_cell),
            source=source,
        )
        if job.company or job.position:
            jobs.append(job)
    return jobs
