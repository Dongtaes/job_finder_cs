"""Build the HTML digest and send it over SMTP (or write it out on a dry run)."""
import html
import re
import smtplib
import ssl
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config
from .geofilter import GROUP_GERMANY, GROUP_EUROPE, GROUP_REMOTE

GROUP_ORDER = [GROUP_GERMANY, GROUP_EUROPE, GROUP_REMOTE]

# Approximate age in days per unit, for freshest-first sorting.
_AGE_UNIT_DAYS = {"h": 1 / 24, "d": 1.0, "w": 7.0, "mo": 30.0, "m": 30.0, "y": 365.0}
_AGE_RE = re.compile(r"(\d+)\s*(mo|[hdwmy])", re.IGNORECASE)


def _age_days(age):
    """Parse an age string like '3d', '5h', '2w' into a number of days.

    Unknown/empty ages sort to the very end (treated as very old).
    """
    m = _AGE_RE.search(age or "")
    if not m:
        return float("inf")
    return int(m.group(1)) * _AGE_UNIT_DAYS.get(m.group(2).lower(), 1.0)

_STYLES = """
body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
       color: #1a1a1a; line-height: 1.4; }
h2 { border-bottom: 2px solid #eee; padding-bottom: 4px; margin-top: 28px; }
table { border-collapse: collapse; width: 100%; margin-bottom: 8px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid #eee;
         font-size: 14px; vertical-align: top; }
th { background: #f6f8fa; font-size: 12px; text-transform: uppercase; color: #555; }
.company { font-weight: 600; }
.src { display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 8px;
       background: #eef; color: #339; margin-left: 6px; }
a.apply { display: inline-block; padding: 4px 12px; background: #2563eb; color: #fff;
          border-radius: 6px; text-decoration: none; font-size: 13px; }
.muted { color: #888; font-size: 12px; }
.section.highlight { background: #fff7ed; border: 2px solid #f59e0b;
                     border-radius: 10px; padding: 6px 16px 12px; margin-top: 20px; }
.section.highlight h2 { color: #b45309; border-bottom-color: #fcd34d; }
.note { color: #b45309; font-weight: 600; font-size: 13px; margin: 6px 0 8px; }
"""


def _esc(text):
    return html.escape(text or "")


def _row_html(job):
    company = _esc(job.company)
    if job.company_url:
        company = f'<a href="{_esc(job.company_url)}">{company}</a>'
    apply = ""
    if job.apply_url:
        apply = f'<a class="apply" href="{_esc(job.apply_url)}">Apply</a>'
    location = _esc(job.location) or '<span class="muted">unspecified</span>'
    return (
        "<tr>"
        f'<td class="company">{company}<span class="src">{_esc(job.source)}</span></td>'
        f"<td>{_esc(job.position)}</td>"
        f"<td>{location}</td>"
        f'<td class="muted">{_esc(job.age)}</td>'
        f"<td>{apply}</td>"
        "</tr>"
    )


def _group_html(title, jobs, highlight=False):
    if not jobs:
        return ""
    rows = "\n".join(_row_html(j) for j in jobs)
    cls = "section highlight" if highlight else "section"
    flag = "🇩🇪 " if highlight else ""
    note = (
        "<p class='note'>⭐ Top priority — roles located in Germany.</p>"
        if highlight
        else ""
    )
    return (
        f"<div class='{cls}'>"
        f"<h2>{flag}{_esc(title)} <span class='muted'>({len(jobs)})</span></h2>"
        f"{note}"
        "<table><thead><tr>"
        "<th>Company</th><th>Position</th><th>Location</th><th>Age</th><th></th>"
        "</tr></thead><tbody>"
        f"{rows}</tbody></table>"
        "</div>"
    )


def build_html(jobs, category="Roles"):
    """Render the grouped HTML digest for ``jobs`` (each must have ``.group``).

    Germany is shown first and visually highlighted as the top-priority group.
    ``category`` labels the digest (e.g. "Internships", "New Grad").
    """
    by_group = {g: [] for g in GROUP_ORDER}
    for job in jobs:
        by_group.setdefault(job.group, []).append(job)
    # Freshest first; company/position break ties for equal ages.
    for group_jobs in by_group.values():
        group_jobs.sort(key=lambda j: (_age_days(j.age), j.company.lower(), j.position.lower()))

    sections = "\n".join(
        _group_html(g, by_group.get(g, []), highlight=(g == GROUP_GERMANY))
        for g in GROUP_ORDER
    )
    counts = {g: len(by_group.get(g, [])) for g in GROUP_ORDER}
    today = date.today().isoformat()
    return (
        f"<html><head><meta charset='utf-8'><style>{_STYLES}</style></head><body>"
        f"<h1 style='font-size:20px;margin:0 0 4px'>{_esc(category)}</h1>"
        f"<p class='muted'>Daily {_esc(category)} digest &middot; {today} &middot; "
        f"{len(jobs)} new role(s) &middot; "
        f"🇩🇪 {counts[GROUP_GERMANY]} Germany &middot; "
        f"{counts[GROUP_EUROPE]} Europe &middot; "
        f"{counts[GROUP_REMOTE]} remote/unspecified</p>"
        f"{sections}"
        "<p class='muted'>Sources: speedyapply 2027 SWE &amp; AI College Jobs "
        "(international).</p>"
        "</body></html>"
    )


def subject_line(jobs, category="Roles"):
    germany = sum(1 for j in jobs if j.group == GROUP_GERMANY)
    other = len(jobs) - germany
    return (
        f"🇩🇪 {germany} Germany + {other} EU/remote {category} "
        f"— {date.today().isoformat()}"
    )


def send(jobs, category="Roles", out_path="out.html"):
    """Send the digest via SMTP, or write it to ``out_path`` on a dry run.

    Returns the rendered HTML.
    """
    body = build_html(jobs, category)

    if config.is_dry_run():
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        print(f"[dry-run] wrote {category} digest to {out_path}")
        return body

    cfg = config.smtp_config()
    missing = [k for k in ("username", "password", "recipient") if not cfg[k]]
    if missing:
        raise RuntimeError(f"Missing SMTP config: {', '.join(missing)}")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject_line(jobs, category)
    msg["From"] = cfg["username"]
    msg["To"] = cfg["recipient"]
    msg.attach(MIMEText(body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=context) as server:
        server.login(cfg["username"], cfg["password"])
        server.sendmail(cfg["username"], [cfg["recipient"]], msg.as_string())
    print(f"Sent {category} digest with {len(jobs)} role(s) to {cfg['recipient']}")
    return body
