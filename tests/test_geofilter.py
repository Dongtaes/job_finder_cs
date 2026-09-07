from jobfinder import geofilter
from jobfinder.geofilter import GROUP_GERMANY, GROUP_EUROPE, GROUP_REMOTE
from jobfinder.parse import Job


def make(location):
    return Job(
        company="X",
        company_url="",
        position="Intern",
        location=location,
        apply_url=f"https://apply/{location}",
        age="1d",
        source="SWE",
    )


def test_classify_germany():
    assert geofilter.classify("Berlin, Germany") == GROUP_GERMANY
    assert geofilter.classify("Munich, Germany +1") == GROUP_GERMANY


def test_classify_europe():
    assert geofilter.classify("Veldhoven, Netherlands") == GROUP_EUROPE
    assert geofilter.classify("London, United Kingdom") == GROUP_EUROPE
    assert geofilter.classify("Dublin, UK") == GROUP_EUROPE


def test_classify_remote_and_blank():
    assert geofilter.classify("") == GROUP_REMOTE
    assert geofilter.classify("Remote") == GROUP_REMOTE
    assert geofilter.classify("EMEA") == GROUP_REMOTE
    assert geofilter.classify("Remote, EMEA") == GROUP_REMOTE


def test_classify_remote_uses_country():
    # A remote role tied to a country is judged by that country.
    assert geofilter.classify("Remote - France") == GROUP_EUROPE
    assert geofilter.classify("Remote - Lithuania +1") == GROUP_EUROPE
    assert geofilter.classify("Remote - Berlin, Germany") == GROUP_GERMANY
    assert geofilter.classify("Remote - Québec, Canada") is None
    assert geofilter.classify("Remote - Gurugram, India") is None


def test_classify_dropped():
    assert geofilter.classify("Bengaluru, India") is None
    assert geofilter.classify("Waterloo, Canada +2") is None
    assert geofilter.classify("New York, USA") is None


def test_filter_jobs_keeps_and_labels():
    jobs = [
        make("Berlin, Germany"),
        make("Paris, France"),
        make("Bengaluru, India"),
        make(""),
    ]
    kept = geofilter.filter_jobs(jobs)
    groups = sorted(j.group for j in kept)
    assert len(kept) == 3
    assert groups == [GROUP_EUROPE, GROUP_GERMANY, GROUP_REMOTE]


def test_classify_uses_resolved_hidden_locations():
    # "+1" hides a German site: the role must be promoted, not dropped.
    assert geofilter.classify(
        "Vancouver, Canada +1", ["Vancouver, Canada", "Munich, Germany"]
    ) == GROUP_GERMANY
    # Europe beats a non-European first city.
    assert geofilter.classify(
        "Tel Aviv, Israel +1", ["Tel Aviv, Israel", "Dublin, Ireland"]
    ) == GROUP_EUROPE
    # A better group in the visible cell is never downgraded by the extras.
    assert geofilter.classify(
        "Munich, Germany +1", ["Munich, Germany", "Bengaluru, India"]
    ) == GROUP_GERMANY
    # All hidden sites non-European: still dropped.
    assert geofilter.classify(
        "Waterloo, Canada +1", ["Waterloo, Canada", "Toronto, Canada"]
    ) is None


def test_classify_country_order_independent():
    # Workday reports "Country, City"; Greenhouse "City, Country".
    assert geofilter.classify("Germany, Munich") == GROUP_GERMANY
    assert geofilter.classify("China, Beijing") is None


def test_classify_bare_city_fallback():
    # Lever and Google often give a city with no country at all.
    assert geofilter.classify("Munich") == GROUP_GERMANY
    assert geofilter.classify("Zurich") == GROUP_EUROPE
    assert geofilter.classify("Bengaluru") is None
    # A named non-European country wins over a same-named European city.
    assert geofilter.classify("London, Canada") is None
    assert geofilter.classify("London, United Kingdom") == GROUP_EUROPE


def test_filter_jobs_keeps_resolved_germany():
    job = make("Vancouver, Canada +1")
    job.resolved_locations = ["Vancouver, Canada", "Munich, Germany"]
    kept = geofilter.filter_jobs([job, make("Waterloo, Canada +2")])
    assert [j.group for j in kept] == [GROUP_GERMANY]


def test_display_location_shows_resolved_list():
    job = make("Vancouver, Canada +1")
    assert geofilter.display_location(job) == "Vancouver, Canada +1"
    job.resolved_locations = ["Vancouver, Canada", "Munich, Germany"]
    assert geofilter.display_location(job) == "Vancouver, Canada · Munich, Germany"


def test_classify_ignores_parenthetical_qualifiers():
    # Grafana-style "Spain (Remote)" must still read as its country.
    assert geofilter.classify("Remote - EMEA +1", ["EMEA", "Spain (Remote)"]) == GROUP_EUROPE
    assert geofilter.classify("Munich (Hybrid), Germany") == GROUP_GERMANY


def test_classify_bare_city_respects_non_european_regions():
    # "Cambridge, Ontario" names no country but is plainly not Cambridge UK.
    assert geofilter.classify("Cambridge, Ontario") is None
    assert geofilter.classify(
        "Cambridge, Canada +1", ["Cambridge, Ontario", "Toronto, Ontario"]
    ) is None
