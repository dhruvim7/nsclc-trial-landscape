"""Download trial records from the ClinicalTrials.gov v2 API.

The API is public and needs no key. Results are paged with a cursor
(nextPageToken), so the loop runs until the API stops returning a token.

Two parts of the request are "nice to have" rather than essential:
  - filter.advanced, which restricts to interventional studies server-side
  - fields, which trims each record to the fields we use
If the API rejects either one (HTTP 400), the request is retried without it
and the parser does the same job locally. The mode that worked is saved in
data/fetch_meta.json so it is visible in the report.
"""

import json
import time
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import settings


def _session():
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": settings.USER_AGENT, "Accept": "application/json"})
    return s


def _request_variants(condition):
    base = {"query.cond": condition, "countTotal": "true", "format": "json"}
    fields = ",".join(settings.FIELDS)
    interventional = "AREA[StudyType]INTERVENTIONAL"
    return [
        ("server filter + field list", {**base, "filter.advanced": interventional, "fields": fields}),
        ("field list only", {**base, "fields": fields}),
        ("full records", base),
    ]


def _first_page(session, page_size, condition):
    """Try each request variant until one is accepted. Returns (mode, params, payload)."""
    last_error = None
    for mode, params in _request_variants(condition):
        params = {**params, "pageSize": page_size}
        resp = session.get(settings.API_URL, params=params, timeout=settings.TIMEOUT_SECONDS)
        if resp.status_code == 400:
            last_error = resp.text[:300]
            print(f"  API rejected '{mode}' (400). Trying a simpler request.")
            continue
        resp.raise_for_status()
        payload = resp.json()
        if "studies" not in payload:
            raise RuntimeError(f"Unexpected response shape; keys were {list(payload)}")
        return mode, params, payload
    raise RuntimeError(f"All request variants were rejected. Last error: {last_error}")


def fetch_all(condition=settings.CONDITION, refresh=False):
    """Return the list of raw study records, using the local cache when present."""
    if settings.RAW_FILE.exists() and not refresh:
        print(f"Using cached data in {settings.RAW_FILE.name} (run with --refresh to re-download).")
        return json.loads(settings.RAW_FILE.read_text(encoding="utf-8"))

    settings.DATA_DIR.mkdir(exist_ok=True)
    session = _session()
    print(f"Downloading '{condition}' trials from ClinicalTrials.gov ...")

    mode, params, payload = _first_page(session, settings.PAGE_SIZE, condition)
    total = payload.get("totalCount")
    studies = list(payload["studies"])
    print(f"  request mode: {mode}; registry matches: {total}")

    token = payload.get("nextPageToken")
    while token:
        time.sleep(settings.PAUSE_SECONDS)
        resp = session.get(settings.API_URL, params={**params, "pageToken": token},
                           timeout=settings.TIMEOUT_SECONDS)
        resp.raise_for_status()
        payload = resp.json()
        studies.extend(payload.get("studies", []))
        token = payload.get("nextPageToken")
        print(f"  {len(studies):,} records")

    if total is not None and len(studies) != total:
        print(f"  WARNING: downloaded {len(studies):,} records but the registry reported {total:,}.")

    settings.RAW_FILE.write_text(json.dumps(studies), encoding="utf-8")
    settings.META_FILE.write_text(json.dumps({
        "condition": condition,
        "downloaded_on": date.today().isoformat(),
        "request_mode": mode,
        "registry_total": total,
        "records_downloaded": len(studies),
    }, indent=2), encoding="utf-8")
    print(f"Saved {len(studies):,} records.")
    return studies


def check(condition=settings.CONDITION):
    """Quick live test: fetch three records and show how they parse."""
    from .parse import parse_study

    session = _session()
    mode, _, payload = _first_page(session, 3, condition)
    print(f"Request mode accepted: {mode}")
    print(f"Registry matches for '{condition}': {payload.get('totalCount')}")
    for study in payload["studies"]:
        row = parse_study(study)
        print("-" * 60)
        for key in ("nct_id", "study_type", "status", "phase", "sponsor", "sponsor_class",
                    "start_date", "start_date_type", "completion_date", "enrollment",
                    "n_countries", "drugs"):
            print(f"  {key:<18} {row.get(key)}")
    return mode
