# Germany/Europe Jobs Daily Digest

Fetches listings from the speedyapply job boards, keeps roles in **Germany**,
**wider Europe**, or with **unspecified/remote** locations, and emails a digest of
**only the new roles** since the last run.

It runs **two independent pipelines**, each sending its own email:

| Category        | Source files (SWE + AI)      | State file               |
|-----------------|------------------------------|--------------------------|
| **Internships** | `INTERN_INTL.md`             | `data/seen.json`         |
| **New Grad**    | `NEW_GRAD_INTL.md`           | `data/seen_newgrad.json` |

Sources:
- [2027 SWE College Jobs](https://github.com/speedyapply/2027-SWE-College-Jobs) — `INTERN_INTL.md`, `NEW_GRAD_INTL.md`
- [2027 AI College Jobs](https://github.com/speedyapply/2027-AI-College-Jobs) — `INTERN_INTL.md`, `NEW_GRAD_INTL.md`

## How it works

`main.py` runs each category in `config.CATEGORIES` as a separate pipeline:

1. `jobfinder/fetch.py` downloads the raw markdown for that category's sources.
2. `jobfinder/parse.py` turns the HTML-cell markdown tables into `Job` objects.
3. `jobfinder/geofilter.py` keeps Germany / Europe / unspecified roles and labels each group.
4. `jobfinder/state.py` compares against the category's state file to find new roles.
5. `jobfinder/email_report.py` builds a grouped HTML digest (Germany highlighted and
   first, then Europe, then Remote/Unspecified; freshest first within each group) and
   sends it via SMTP.

Jobs are de-duplicated by their apply URL. Each state file is rewritten every run to the
set of currently-live roles (so stale entries self-prune) and committed back by CI.

## Local usage

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Dry run: fetch + filter for real, write a digest per category (no email sent).
DRY_RUN=1 python main.py
xdg-open out-internships.html out-new-grad.html   # eyeball the results

# Run the tests
pip install pytest
pytest
```

A second consecutive real run reports `0 new` for each category and sends nothing.

## Sending email (Gmail)

Uses Gmail SMTP over SSL (`smtp.gmail.com:465`). Create an **App Password**
(Google Account → Security → 2-Step Verification → App passwords) — a normal
account password will not work.

Environment variables:

| Variable        | Meaning                                   |
|-----------------|-------------------------------------------|
| `MAIL_USERNAME` | Gmail address to send from                |
| `MAIL_PASSWORD` | Gmail **app password**                    |
| `MAIL_TO`       | Recipient (defaults to `MAIL_USERNAME`)   |
| `SMTP_HOST`     | Override SMTP host (default `smtp.gmail.com`) |
| `SMTP_PORT`     | Override SMTP port (default `465`)        |
| `DRY_RUN`       | If set (`1`), write `out-<category>.html` instead of sending |

Real send locally (sends one email per category):

```bash
MAIL_USERNAME=you@gmail.com MAIL_PASSWORD='app password' MAIL_TO=you@gmail.com python main.py
```

## Scheduled runs (GitHub Actions)

`.github/workflows/daily-jobs.yml` runs daily at 06:00 UTC (and on manual dispatch).

Setup:
1. Push this repo to GitHub.
2. Repo → Settings → Secrets and variables → Actions → add `MAIL_USERNAME`,
   `MAIL_PASSWORD`, `MAIL_TO`.
3. Actions tab → *Daily Germany/Europe Jobs* → **Run workflow** to test.

The workflow commits the updated state files (`data/seen.json`,
`data/seen_newgrad.json`) back to the repo so the "new roles only" state persists across
runs. It runs `git pull --rebase --autostash` before committing so the push always
fast-forwards.

## Part 2 (deferred)

Automated application submission and per-role CV/cover-letter tailoring are intentionally
out of scope for now — to be designed separately once this digest is running.
