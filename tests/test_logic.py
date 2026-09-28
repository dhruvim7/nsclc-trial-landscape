import pandas as pd
import pytest

from ctlandscape import analyze as an
from ctlandscape.mechanisms import classify_drug, classify_trial


@pytest.mark.parametrize("name, expected", [
    ("Pembrolizumab", "PD-1/PD-L1"),
    ("MK-3475", "PD-1/PD-L1"),
    ("pembrolizumab 200 mg IV q3w", "PD-1/PD-L1"),
    ("Trastuzumab deruxtecan", "ADC"),
    ("DS-8201a", "ADC"),
    ("Ivonescimab", "PD-1-based bispecific"),
    ("AMG 510", "KRAS"),
    ("Amivantamab", "EGFR"),
    ("Crizotinib", "ALK/ROS1"),
    ("Carboplatin", None),
    ("Placebo", None),
])
def test_classify_drug(name, expected):
    assert classify_drug(name) == expected


def test_classify_trial_is_ordered_and_unique():
    assert classify_trial(["Nivolumab", "Ipilimumab", "Nivolumab"]) == ["PD-1/PD-L1", "CTLA-4"]


@pytest.mark.parametrize("text, expected", [
    ("Slow accrual", "Slow or low accrual"),
    ("Poor enrollment", "Slow or low accrual"),
    ("Business decision", "Business / sponsor decision"),
    ("Study stopped for futility", "Efficacy / futility"),
    ("Unacceptable toxicity", "Safety / toxicity"),
    ("PI left the institution", "Investigator / site"),
    ("", "Not reported"),
    (None, "Not reported"),
    ("Other reasons", "Other"),
])
def test_reason_category(text, expected):
    assert an.reason_category(text) == expected


def _frame(rows):
    df = pd.DataFrame(rows, columns=["nct_id", "status", "phase", "sponsor_class", "sponsor", "start_year"])
    df["start_year"] = df["start_year"].astype("Int64")
    return df


def test_stop_rate_ignores_ongoing_trials():
    df = _frame([
        ("a", "COMPLETED", "Phase 2", "INDUSTRY", "X", 2020),
        ("b", "TERMINATED", "Phase 2", "INDUSTRY", "X", 2020),
        ("c", "WITHDRAWN", "Phase 2", "INDUSTRY", "X", 2020),
        ("d", "RECRUITING", "Phase 2", "INDUSTRY", "X", 2020),
        ("e", "UNKNOWN", "Phase 2", "INDUSTRY", "X", 2020),
    ])
    out = an.stop_rates(df)
    row = out[out["group"] == "Industry"].iloc[0]
    assert row["finished"] == 3 and row["stopped"] == 2 and row["stop_pct"] == 66.7


def test_concentration_hhi():
    span = an.RECENT
    y = span[0]
    df = _frame([(str(i), "RECRUITING", "Phase 3", "INDUSTRY", s, y)
                 for i, s in enumerate(["A"] * 5 + ["B"] * 5)] +
                [("z", "RECRUITING", "Phase 3", "OTHER", "Univ", y),
                 ("m", "RECRUITING", "Phase 3", "INDUSTRY", "A", None)])
    out = an.concentration(df, span)
    assert out["industry_trials"] == 10          # academic and undated trials excluded
    assert out["hhi"] == 5000                    # two sponsors at 50% each
    assert out["top5_pct"] == 100.0


def test_sanity_check_flags_implausible_stop_rate():
    df = _frame([(str(i), "TERMINATED", "Phase 2", "INDUSTRY", "X", 2020) for i in range(150)] +
                [(f"c{i}", "COMPLETED", "Phase 2", "OTHER", "U", 2020) for i in range(100)])
    df["mechanisms"] = ""
    notes = an.sanity_checks(df)
    assert any("Stop rate" in n for n in notes)
