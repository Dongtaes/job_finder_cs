"""Configuration: source URLs, country lists, and environment/secret reading."""
import os

_SWE = "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main"
_AI = "https://raw.githubusercontent.com/speedyapply/2027-AI-College-Jobs/main"

# Each category is an independent pipeline: its own raw sources (tagged by
# source label), its own persisted state file, and its own email.
CATEGORIES = {
    "Internships": {
        "state": "seen.json",
        "locations": "locations.json",
        "sources": {
            "SWE": f"{_SWE}/INTERN_INTL.md",
            "AI": f"{_AI}/INTERN_INTL.md",
        },
    },
    "New Grad": {
        "state": "seen_newgrad.json",
        "locations": "locations_newgrad.json",
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
    "republic of ireland",
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

# Countries we explicitly know are outside Europe. Used to tell "the last segment
# is a country we simply don't keep" from "the last segment is a bare city", so
# that "London, Canada" is not mistaken for the European London.
NON_EUROPE_COUNTRIES = {
    "usa",
    "us",
    "united states",
    "united states of america",
    "canada",
    "mexico",
    "brazil",
    "argentina",
    "chile",
    "colombia",
    "peru",
    "india",
    "china",
    "hong kong",
    "taiwan",
    "japan",
    "south korea",
    "korea",
    "singapore",
    "malaysia",
    "indonesia",
    "thailand",
    "vietnam",
    "philippines",
    "australia",
    "new zealand",
    "israel",
    "turkey",
    "united arab emirates",
    "uae",
    "saudi arabia",
    "qatar",
    "egypt",
    "south africa",
    "nigeria",
    "kenya",
    "morocco",
    "pakistan",
    "bangladesh",
    "sri lanka",
    "russia",
    "ukraine",
    "belarus",
    "costa rica",
    "uruguay",
}

# States and provinces that place a bare city outside Europe: postings often give
# "Cambridge, Ontario" with no country at all, which must not read as Cambridge UK.
NON_EUROPE_REGIONS = {
    "ontario",
    "quebec",
    "québec",
    "british columbia",
    "alberta",
    "manitoba",
    "saskatchewan",
    "nova scotia",
    "new brunswick",
    "newfoundland and labrador",
    "prince edward island",
    "california",
    "texas",
    "new york state",
    "washington",
    "massachusetts",
    "illinois",
    "florida",
    "georgia",
    "virginia",
    "colorado",
    "arizona",
    "oregon",
    "michigan",
    "ohio",
    "pennsylvania",
    "north carolina",
    "new jersey",
    "maharashtra",
    "karnataka",
    "telangana",
    "tamil nadu",
    "haryana",
    "uttar pradesh",
    "ontario province",
}

# Resolved postings often name a city with no country (Lever's "Zurich", Google's
# "Munich"). These sets classify such bare cities; only consulted when the string
# carries no recognizable country.
GERMAN_CITIES = {
    "berlin",
    "munich",
    "münchen",
    "muenchen",
    "hamburg",
    "frankfurt",
    "frankfurt am main",
    "cologne",
    "köln",
    "koeln",
    "stuttgart",
    "düsseldorf",
    "dusseldorf",
    "duesseldorf",
    "leipzig",
    "dresden",
    "nuremberg",
    "nürnberg",
    "nuernberg",
    "hannover",
    "hanover",
    "bremen",
    "essen",
    "dortmund",
    "bonn",
    "münster",
    "muenster",
    "mannheim",
    "karlsruhe",
    "heidelberg",
    "darmstadt",
    "aachen",
    "freiburg",
    "ulm",
    "regensburg",
    "erlangen",
    "ingolstadt",
    "wolfsburg",
    "walldorf",
    "böblingen",
    "boeblingen",
    "sindelfingen",
    "potsdam",
    "kiel",
    "braunschweig",
    "saarbrücken",
    "saarbruecken",
    "chemnitz",
    "jena",
    "würzburg",
    "wuerzburg",
    "augsburg",
    "bochum",
    "bielefeld",
    "wolfratshausen",
}

EUROPE_CITIES = {
    "vienna",
    "graz",
    "linz",
    "zurich",
    "zürich",
    "geneva",
    "basel",
    "lausanne",
    "bern",
    "amsterdam",
    "rotterdam",
    "eindhoven",
    "utrecht",
    "the hague",
    "delft",
    "veldhoven",
    "brussels",
    "antwerp",
    "leuven",
    "ghent",
    "paris",
    "lyon",
    "toulouse",
    "grenoble",
    "nantes",
    "lille",
    "sophia antipolis",
    "dublin",
    "cork",
    "london",
    "cambridge",
    "oxford",
    "manchester",
    "edinburgh",
    "glasgow",
    "bristol",
    "leeds",
    "belfast",
    "reading",
    "madrid",
    "barcelona",
    "valencia",
    "seville",
    "malaga",
    "lisbon",
    "porto",
    "braga",
    "milan",
    "rome",
    "turin",
    "bologna",
    "asti",
    "warsaw",
    "krakow",
    "kraków",
    "cracow",
    "wroclaw",
    "wrocław",
    "gdansk",
    "gdańsk",
    "poznan",
    "poznań",
    "stockholm",
    "gothenburg",
    "malmo",
    "malmö",
    "lund",
    "copenhagen",
    "aarhus",
    "oslo",
    "trondheim",
    "helsinki",
    "espoo",
    "tampere",
    "prague",
    "brno",
    "bratislava",
    "budapest",
    "bucharest",
    "cluj",
    "cluj-napoca",
    "iasi",
    "timisoara",
    "sofia",
    "plovdiv",
    "athens",
    "thessaloniki",
    "zagreb",
    "ljubljana",
    "belgrade",
    "tallinn",
    "vilnius",
    "kaunas",
    "riga",
    "luxembourg",
    "reykjavik",
}

# Cached location lookups (per category, committed by CI alongside the
# seen-job state) for postings whose markdown row hides locations behind "+N".
# Days a cached lookup stays valid: successes rarely change, failures are worth
# retrying sooner in case the posting or the network was briefly unavailable.
LOCATION_TTL_DAYS = 30
LOCATION_FAILURE_TTL_DAYS = 3
# Per-request timeout and thread count for the posting lookups.
RESOLVE_TIMEOUT = 15
RESOLVE_WORKERS = 8


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


def resolve_enabled():
    """Whether to re-read postings to recover locations hidden behind "+N"."""
    return os.environ.get("RESOLVE_LOCATIONS", "").strip() not in ("0", "false", "False")
