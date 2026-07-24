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
