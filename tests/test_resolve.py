import json
from datetime import date, timedelta

import pytest

from jobfinder import resolve
from jobfinder.parse import Job


def make(location, apply_url="https://apply/1"):
    return Job(
        company="X",
        company_url="",
        position="Intern",
        location=location,
        apply_url=apply_url,
        age="1d",
        source="SWE",
    )


def test_hidden_count():
    assert resolve.hidden_count("Warsaw, Poland +1") == 1
    assert resolve.hidden_count("Québec, Canada +3") == 3
    assert resolve.hidden_count("Berlin, Germany") == 0
    assert resolve.hidden_count("") == 0


# --- per-ATS handlers, fed canned API payloads ------------------------------

def fake_get(payloads):
    def _get(url, as_json=True):
        for fragment, value in payloads.items():
            if fragment in url:
                return value
        return None
    return _get


def test_ashby_uses_secondary_locations(monkeypatch):
    payload = {
        "jobs": [
            {
                "id": "abc",
                "location": "Vancouver, British Columbia",
                "address": {"postalAddress": {"addressCountry": "Canada"}},
                "secondaryLocations": [
                    {
                        "location": "Munich",
                        "address": {"postalAddress": {"addressCountry": "Germany"}},
                    }
                ],
            }
        ]
    }
    monkeypatch.setattr(resolve, "_get", fake_get({"posting-api": payload}))
    assert resolve.resolve("https://jobs.ashbyhq.com/rivian/abc") == [
        "Vancouver, British Columbia, Canada",
        "Munich, Germany",
    ]


def test_greenhouse_splits_combined_location(monkeypatch):
    payload = {
        "location": {"name": "Berlin, Germany; Paris, France"},
        "offices": [{"name": "Berlin, Germany"}],
    }
    monkeypatch.setattr(resolve, "_get", fake_get({"api.greenhouse.io": payload}))
    found = resolve.resolve("https://job-boards.eu.greenhouse.io/acme/jobs/123")
    assert found == ["Berlin, Germany", "Paris, France"]


def test_lever_uses_all_locations(monkeypatch):
    payload = {"categories": {"location": "Zurich", "allLocations": ["Zurich", "Munich"]}}
    monkeypatch.setattr(resolve, "_get", fake_get({"api.lever.co": payload}))
    assert resolve.resolve("https://jobs.lever.co/rai/xyz") == ["Zurich", "Munich"]


def test_workable_joins_city_and_country(monkeypatch):
    payload = {
        "locations": [
            {"city": "Munich", "country": "Germany"},
            {"city": "Berlin", "country": "Germany"},
        ]
    }
    monkeypatch.setattr(resolve, "_get", fake_get({"apply.workable.com/api": payload}))
    found = resolve.resolve("https://apply.workable.com/fioneer/j/44D6/")
    assert found == ["Munich, Germany", "Berlin, Germany"]


def test_workday_uses_additional_locations(monkeypatch):
    payload = {
        "jobPostingInfo": {
            "location": "China, Beijing",
            "additionalLocations": ["Germany, Munich"],
        }
    }
    captured = {}

    def _get(url, as_json=True):
        captured["url"] = url
        return payload

    monkeypatch.setattr(resolve, "_get", _get)
    url = ("https://nvidia.wd5.myworkdayjobs.com/en-US/nvidiaexternalcareersite"
           "/job/China-Beijing/Intern_JR1")
    assert resolve.resolve(url) == ["China, Beijing", "Germany, Munich"]
    assert captured["url"] == (
        "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia"
        "/nvidiaexternalcareersite/job/China-Beijing/Intern_JR1"
    )


def test_google_reads_location_spans(monkeypatch):
    html = (
        '<span class="r0wTof ">Mountain View, CA, USA</span>'
        + "<div>" + "x" * 400 + "</div>"
        + '<span class="r0wTof ">Warsaw, Poland</span>'
        '<span class="r0wTof p3oCrc">; Kraków, Poland</span>'
    )
    monkeypatch.setattr(resolve, "_get", lambda url, as_json=True: html)
    found = resolve.resolve(
        "https://www.google.com/about/careers/applications/jobs/results/1",
        "Warsaw, Poland +1",
    )
    assert found == ["Warsaw, Poland", "Kraków, Poland"]


def test_generic_falls_back_to_json_ld(monkeypatch):
    html = (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "jobLocation": [
                    {"address": {"addressLocality": "Munich", "addressCountry": "DE"}},
                    {"address": {"addressLocality": "Austin", "addressCountry": "US"}},
                ],
            }
        )
        + "</script>"
    )
    monkeypatch.setattr(resolve, "_get", lambda url, as_json=True: html)
    assert resolve.resolve("https://careers.example.com/jobs/1") == [
        "Munich, Germany",
        "Austin, USA",
    ]


def test_handler_failure_falls_back_to_generic(monkeypatch):
    monkeypatch.setattr(resolve, "_get", lambda url, as_json=True: None)
    assert resolve.resolve("https://jobs.ashbyhq.com/acme/abc") == []


# --- cache behaviour ---------------------------------------------------------

def test_resolve_jobs_only_looks_up_hidden_rows(tmp_path):
    calls = []

    def resolver(url, hint=""):
        calls.append(url)
        return ["Munich, Germany"]

    jobs = [
        make("Vancouver, Canada +1", "https://apply/a"),
        make("Berlin, Germany", "https://apply/b"),
    ]
    resolve.resolve_jobs(jobs, str(tmp_path / "loc.json"), resolver=resolver)
    assert calls == ["https://apply/a"]
    assert jobs[0].resolved_locations == ["Munich, Germany"]
    assert jobs[1].resolved_locations == []


def test_resolve_jobs_reuses_fresh_cache(tmp_path):
    path = str(tmp_path / "loc.json")
    jobs = [make("Vancouver, Canada +1", "https://apply/a")]
    resolve.resolve_jobs(jobs, path, resolver=lambda url, hint='': ["Munich, Germany"])

    again = [make("Vancouver, Canada +1", "https://apply/a")]
    resolve.resolve_jobs(again, path, resolver=_never_called)
    assert again[0].resolved_locations == ["Munich, Germany"]


def _never_called(url, hint=""):
    raise AssertionError(f"unexpected lookup for {url}")


def test_resolve_jobs_retries_stale_failures(tmp_path):
    path = str(tmp_path / "loc.json")
    jobs = [make("Vancouver, Canada +1", "https://apply/a")]
    stale = date.today() - timedelta(days=5)
    resolve.resolve_jobs(jobs, path, resolver=lambda url, hint='': [], today=stale)
    assert jobs[0].resolved_locations == []

    retried = [make("Vancouver, Canada +1", "https://apply/a")]
    resolve.resolve_jobs(retried, path, resolver=lambda url, hint='': ["Munich, Germany"])
    assert retried[0].resolved_locations == ["Munich, Germany"]


def test_resolve_jobs_keeps_fresh_successes(tmp_path):
    path = str(tmp_path / "loc.json")
    jobs = [make("Vancouver, Canada +1", "https://apply/a")]
    recent = date.today() - timedelta(days=5)
    resolve.resolve_jobs(jobs, path, resolver=lambda url, hint='': ["Munich, Germany"], today=recent)

    again = [make("Vancouver, Canada +1", "https://apply/a")]
    resolve.resolve_jobs(again, path, resolver=_never_called)
    assert again[0].resolved_locations == ["Munich, Germany"]


def test_resolve_jobs_prunes_dead_urls(tmp_path):
    path = str(tmp_path / "loc.json")
    resolve.resolve_jobs(
        [make("Vancouver, Canada +1", "https://apply/old")],
        path,
        resolver=lambda url, hint='': ["Munich, Germany"],
    )
    resolve.resolve_jobs(
        [make("Toronto, Canada +1", "https://apply/new")],
        path,
        resolver=lambda url, hint='': ["Berlin, Germany"],
    )
    cache = resolve.load_cache(path)
    assert list(cache) == ["https://apply/new"]


def test_load_cache_tolerates_garbage(tmp_path):
    path = tmp_path / "loc.json"
    path.write_text("not json", encoding="utf-8")
    assert resolve.load_cache(str(path)) == {}


def test_google_ignores_other_postings_on_the_page(monkeypatch):
    html = (
        '<span class="r0wTof ">Munich, Germany</span>'
        + "<div>" + "x" * 400 + "</div>"
        + '<span class="r0wTof ">Waterloo, ON, Canada</span>'
        '<span class="r0wTof p3oCrc">; Toronto, ON, Canada</span>'
    )
    monkeypatch.setattr(resolve, "_get", lambda url, as_json=True: html)
    found = resolve.resolve(
        "https://www.google.com/about/careers/applications/jobs/results/1",
        "Waterloo, Canada +1",
    )
    assert found == ["Waterloo, ON, Canada", "Toronto, ON, Canada"]


def test_resolve_jobs_passes_the_visible_location_as_hint(tmp_path):
    seen = {}

    def resolver(url, hint=""):
        seen[url] = hint
        return ["Munich, Germany"]

    jobs = [make("Warsaw, Poland +1", "https://apply/a")]
    resolve.resolve_jobs(jobs, str(tmp_path / "loc.json"), resolver=resolver)
    assert seen == {"https://apply/a": "Warsaw, Poland +1"}
