"""End-to-end run with the network replaced by a fake API."""

import json

import pytest

from ctlandscape import __main__ as cli
from ctlandscape import fetch, settings
from tests.sample_data import synthetic


class FakeResponse:
    def __init__(self, status, payload=None):
        self.status_code, self._payload, self.text = status, payload, json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    """Serves the synthetic records in pages; optionally rejects the first request mode."""

    def __init__(self, records, page_size=150, reject_advanced=False):
        self.records, self.page_size, self.reject_advanced = records, page_size, reject_advanced
        self.headers, self.calls = {}, []

    def mount(self, *a):
        pass

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        if self.reject_advanced and "filter.advanced" in params:
            return FakeResponse(400, {"error": "bad filter"})
        start = int(params.get("pageToken", 0))
        size = min(int(params["pageSize"]), self.page_size)
        page = self.records[start:start + size]
        body = {"studies": page}
        if start == 0:
            body["totalCount"] = len(self.records)
        if start + size < len(self.records):
            body["nextPageToken"] = str(start + size)
        return FakeResponse(200, body)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    for name, sub in (("DATA_DIR", "data"), ("FIG_DIR", "figures"), ("REPORT_DIR", "reports")):
        monkeypatch.setattr(settings, name, tmp_path / sub)
    monkeypatch.setattr(settings, "RAW_FILE", tmp_path / "data" / "raw.json")
    monkeypatch.setattr(settings, "META_FILE", tmp_path / "data" / "meta.json")
    monkeypatch.setattr(settings, "CLEAN_FILE", tmp_path / "data" / "clean.csv")
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    monkeypatch.setattr(settings, "PAUSE_SECONDS", 0)
    return tmp_path


def test_pagination_collects_every_record(sandbox, monkeypatch):
    records = synthetic()
    fake = FakeSession(records)
    monkeypatch.setattr(fetch, "_session", lambda: fake)
    got = fetch.fetch_all(refresh=True)
    assert len(got) == len(records)
    meta = json.loads(settings.META_FILE.read_text())
    assert meta["request_mode"] == "server filter + field list"
    assert all(c["query.cond"] == settings.CONDITION for c in fake.calls)


def test_falls_back_when_filter_rejected(sandbox, monkeypatch):
    fake = FakeSession(synthetic(), reject_advanced=True)
    monkeypatch.setattr(fetch, "_session", lambda: fake)
    fetch.fetch_all(refresh=True)
    assert json.loads(settings.META_FILE.read_text())["request_mode"] == "field list only"
    assert "filter.advanced" not in fake.calls[-1]


def test_full_run_writes_all_outputs(sandbox, monkeypatch):
    monkeypatch.setattr(fetch, "_session", lambda: FakeSession(synthetic()))
    cli.run(refresh=True)
    figs = sorted(p.name for p in (sandbox / "figures").glob("*.png"))
    assert len(figs) == 9
    assert (sandbox / "reports" / "numbers.md").stat().st_size > 1000
    assert (sandbox / "data" / "clean.csv").exists()
