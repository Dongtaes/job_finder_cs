"""Configuration: source URLs, country lists, and environment/secret reading."""
import os

_SWE = "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main"
_AI = "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main"

# Each category is an independent pipeline: its own raw sources (tagged by
# source label), its own persisted state file, and its own email.
CATEGORIES = {
    "Internships": {
        "state": "seen.json",
        "sources": {
            "SWE": f"{_SWE}/INTERN_INTL.md",
            "AI": f"{_AI}/INTERN_INTL.md",
        },
    },
    "New Grad": {
        "state": "seen_newgrad.json",
        "sources": {
            "SWE": f"{_SWE}/NEW_GRAD_INTL.md",
            "AI": f"{_AI}/NEW_GRAD_INTL.md",
        },
    },
}

# Country part is grouped as "Germany" on its own; the rest fall under "Europe".
GERMANY = "germany"

# Curated set of European countries to keep (lowercase, matched on the country
# part of the location string). Includes common spelling variants.
EUROPE_COUNTRIES = {
    "germany",
    "austria",
    "switzerland",
    "netherlands",
    "the netherlands",
    "belgium",
    "france",
    "ireland",
    "united kingdom",
    "uk",
    "england",
    "scotland",
    "spain",
    "portugal",
    "italy",
    "poland",
    "sweden",
    "denmark",
    "norway",
    "finland",
    "czechia",
    "czech republic",
    "luxembourg",
    "hungary",
    "romania",
    "greece",
    "estonia",
    "lithuania",
    "latvia",
    "croatia",
    "slovakia",
    "slovenia",
    "bulgaria",
    "iceland",
    "cyprus",
    "malta",
}

# Directory where per-category "seen jobs" state is persisted (committed by CI).
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def state_path(filename):
    return os.path.join(DATA_DIR, filename)


def smtp_config():
    """Read SMTP/recipient settings from the environment.

    Returns a dict; missing values are None so callers can validate.
    """
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "465")),
        "username": os.environ.get("MAIL_USERNAME"),
        "password": os.environ.get("MAIL_PASSWORD"),
        "recipient": os.environ.get("MAIL_TO") or os.environ.get("MAIL_USERNAME"),
    }


def is_dry_run():
    return os.environ.get("DRY_RUN", "").strip() not in ("", "0", "false", "False")
