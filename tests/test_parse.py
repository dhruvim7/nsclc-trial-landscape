from datetime import date

from ctlandscape.parse import parse_date, parse_study, phase_label, to_dataframe
from tests.sample_data import REAL_LOOKING, synthetic


def test_phase_labels():
    assert phase_label(["PHASE1", "PHASE2"]) == "Phase 1/2"
    assert phase_label(["PHASE2", "PHASE1"]) == "Phase 1/2"
    assert phase_label(["PHASE3"]) == "Phase 3"
    assert phase_label(["NA"]) == "No phase"
    assert phase_label([]) == "No phase"
    assert phase_label(None) == "No phase"


def test_dates():
    assert parse_date("2016-03") == date(2016, 3, 1)
    assert parse_date("2018-09-15") == date(2018, 9, 15)
    assert parse_date("") is None
    assert parse_date("not a date") is None


def test_parse_known_record():
    row = parse_study(REAL_LOOKING)
    assert row["nct_id"] == "NCT00000001"
    assert row["phase"] == "Phase 1/2"
    assert row["sponsor_class"] == "INDUSTRY"
    assert row["duration_months"] == 30
    assert row["completion_date_type"] == "ACTUAL"
    assert row["drugs"] == "Osimertinib|MK-3475"        # de-duplicated, procedures dropped
    assert row["mechanisms"] == "PD-1/PD-L1|EGFR"
    assert row["countries"] == "China|United States"
    assert row["n_countries"] == 2
    assert row["why_stopped"] == "Slow accrual"


def test_empty_record_does_not_crash():
    row = parse_study({})
    assert row["nct_id"] is None and row["phase"] == "No phase" and row["n_countries"] == 0


def test_dataframe_filters_and_dedupes():
    raw = synthetic()
    df = to_dataframe(raw)
    assert df["nct_id"].is_unique
    assert set(df["study_type"]) == {"INTERVENTIONAL"}
