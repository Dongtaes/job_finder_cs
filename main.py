"""Run each job category (Internships, New Grad) as an independent pipeline:
fetch -> parse -> filter -> diff against that category's state -> email digest.
"""
import re
import sys

from jobfinder import config, email_report, fetch, geofilter, state
from jobfinder.parse import parse_table


def collect_jobs(sources):
    """Fetch and parse a category's sources into a flat list of Job objects."""
    jobs = []
    for label, markdown in fetch.fetch_all(sources):
        parsed = parse_table(markdown, label)
        print(f"  parsed {len(parsed)} rows from {label}")
        jobs.extend(parsed)
    return jobs


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def run_category(category, cfg):
    """Run one category end-to-end. Returns the count of new roles emailed."""
    print(f"[{category}]")
    jobs = collect_jobs(cfg["sources"])
    kept = geofilter.filter_jobs(jobs)
    print(f"  kept {len(kept)} Germany/Europe/unspecified (of {len(jobs)} total)")

    path = config.state_path(cfg["state"])
    seen = state.load(path)
    new_jobs = [j for j in kept if j.key() not in seen]
    print(f"  {len(new_jobs)} new role(s) since last run")

    if new_jobs:
        email_report.send(new_jobs, category, out_path=f"out-{_slug(category)}.html")
    else:
        print("  nothing new — no email sent.")

    if config.is_dry_run():
        print("  [dry-run] state not persisted.")
    else:
        # Persist the currently-live set so the file self-prunes to what's active.
        state.save({j.key() for j in kept}, path)
    return len(new_jobs)


def main():
    for category, cfg in config.CATEGORIES.items():
        run_category(category, cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
