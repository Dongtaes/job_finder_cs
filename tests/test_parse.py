from jobfinder.parse import parse_table

FIXTURE = """
Some intro text.

| Company | Position | Location | Posting | Age |
|---|---|---|---|---|
| <a href="https://www.rivian.com"><strong>Rivian</strong></a> | Software Integration Engineering Intern | Berlin, Germany | <a href="https://jobs.rivian.com/apply/123"><img src="https://i.imgur.com/JpkfjIq.png" alt="Apply" width="70"/></a> | 4d |
| <a href="https://www.google.com"><strong>Google</strong></a> | Software Developer Intern | Waterloo, Canada +2 | <a href="https://careers.google.com/jobs/999"><img src="x.png" alt="Apply"/></a> | 2d |
| ↳ | Software Developer Intern - MS | Waterloo, Canada +2 | <a href="https://careers.google.com/jobs/1000"><img src="x.png" alt="Apply"/></a> | 2d |
"""


def test_parses_expected_rows():
    jobs = parse_table(FIXTURE, "SWE")
    assert len(jobs) == 3


def test_company_and_links():
    jobs = parse_table(FIXTURE, "SWE")
    rivian = jobs[0]
    assert rivian.company == "Rivian"
    assert rivian.company_url == "https://www.rivian.com"
    assert rivian.position == "Software Integration Engineering Intern"
    assert rivian.location == "Berlin, Germany"
    assert rivian.apply_url == "https://jobs.rivian.com/apply/123"
    assert rivian.age == "4d"
    assert rivian.source == "SWE"


def test_continuation_row_inherits_company():
    jobs = parse_table(FIXTURE, "SWE")
    sub = jobs[2]
    assert sub.company == "Google"
    assert sub.company_url == "https://www.google.com"
    assert sub.apply_url == "https://careers.google.com/jobs/1000"


def test_key_uses_apply_url():
    jobs = parse_table(FIXTURE, "SWE")
    assert jobs[0].key() == "https://jobs.rivian.com/apply/123"
