"""Configuration: source URLs, country lists, and environment/secret reading."""
import os

# Raw markdown sources (tagged by source label).
SOURCES = {
    "SWE": "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/INTERN_INTL.md",
    "AI": "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main/INTERN_INTL.md",
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

# Path where the "seen jobs" state is persisted (committed back by CI).
STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seen.json")


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
