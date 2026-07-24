"""Orchestrate: fetch -> parse -> filter -> diff against state -> email digest."""
import sys

from jobfinder import config, email_report, fetch, geofilter, state
from jobfinder.parse import parse_table


def collect_jobs():
    """Fetch and parse all sources into a flat list of Job objects."""
    jobs = []
    for label, markdown in fetch.fetch_all():
        parsed = parse_table(markdown, label)
        print(f"Parsed {len(parsed)} rows from {label}")
        jobs.extend(parsed)
    return jobs


def main():
    jobs = collect_jobs()
    kept = geofilter.filter_jobs(jobs)
    print(f"Kept {len(kept)} Germany/Europe/unspecified roles (of {len(jobs)} total)")

    seen = state.load()
    new_jobs = [j for j in kept if j.key() not in seen]
    print(f"{len(new_jobs)} new role(s) since last run")

    if new_jobs:
        email_report.send(new_jobs)
    else:
        print("Nothing new — no email sent.")

    # A dry run must not mutate persisted state (it's just for eyeballing output).
    if config.is_dry_run():
        print("[dry-run] state not persisted.")
        return 0

    # Persist the currently-live set so the state file self-prunes to what's active.
    state.save({j.key() for j in kept})
    return 0


if __name__ == "__main__":
    sys.exit(main())
