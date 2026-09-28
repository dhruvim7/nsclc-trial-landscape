"""Turn nested API records into one flat row per trial."""

from datetime import date

import pandas as pd

from .mechanisms import classify_trial

PHASE_LABELS = {
    ("EARLY_PHASE1",): "Early Phase 1",
    ("PHASE1",): "Phase 1",
    ("PHASE1", "PHASE2"): "Phase 1/2",
    ("PHASE2",): "Phase 2",
    ("PHASE2", "PHASE3"): "Phase 2/3",
    ("PHASE3",): "Phase 3",
    ("PHASE4",): "Phase 4",
}
PHASE_ORDER = ["Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3",
               "Phase 3", "Phase 4", "No phase"]

SEP = "|"

# Subsidiaries and name variants merged into the current parent company.
# Merck KGaA (Germany) is a different company from Merck & Co./MSD and is not merged.
SPONSOR_ALIASES = {
    "Genentech, Inc.": "Hoffmann-La Roche",
    "MedImmune LLC": "AstraZeneca",
    "Daiichi Sankyo Co., Ltd.": "Daiichi Sankyo",
    "Seagen, a wholly owned subsidiary of Pfizer": "Pfizer",
    "VelosBio Inc., a subsidiary of Merck & Co., Inc. (Rahway, New Jersey USA)": "Merck Sharp & Dohme LLC",
}


def phase_label(phases):
    key = tuple(sorted(p for p in (phases or []) if p != "NA"))
    if not key:
        return "No phase"
    return PHASE_LABELS.get(key, "No phase")


def parse_date(value):
    """Registry dates are 'YYYY-MM-DD' or 'YYYY-MM'. Month-only dates become the 1st."""
    if not value or not isinstance(value, str):
        return None
    parts = value.strip().split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def months_between(start, end):
    if start is None or end is None:
        return None
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return months if months >= 0 else None


def parse_study(study):
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    design = ps.get("designModule", {})
    arms = ps.get("armsInterventionsModule", {})
    locations = ps.get("contactsLocationsModule", {}).get("locations", []) or []

    start_struct = status.get("startDateStruct") or {}
    end_struct = status.get("completionDateStruct") or {}
    start = parse_date(start_struct.get("date"))
    end = parse_date(end_struct.get("date"))

    interventions = arms.get("interventions", []) or []
    drugs = []
    for item in interventions:
        name = (item.get("name") or "").strip()
        if item.get("type") in ("DRUG", "BIOLOGICAL") and name and name not in drugs:
            drugs.append(name)

    countries = sorted({loc.get("country") for loc in locations if loc.get("country")})

    return {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "study_type": design.get("studyType"),
        "status": status.get("overallStatus"),
        "why_stopped": status.get("whyStopped"),
        "phase": phase_label(design.get("phases")),
        "start_date": start,
        "start_date_type": start_struct.get("type"),
        "start_year": start.year if start else None,
        "completion_date": end,
        "completion_date_type": end_struct.get("type"),
        "duration_months": months_between(start, end),
        "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
        "sponsor": sponsor.get("name"),
        "sponsor_class": sponsor.get("class"),
        "intervention_types": SEP.join(sorted({i.get("type") for i in interventions if i.get("type")})),
        "drugs": SEP.join(drugs),
        "mechanisms": SEP.join(classify_trial(drugs)),
        "countries": SEP.join(countries),
        "n_countries": len(countries),
    }


def to_dataframe(studies, interventional_only=True):
    rows = [parse_study(s) for s in studies]
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No records to parse.")

    df = df.drop_duplicates(subset="nct_id").reset_index(drop=True)
    df["sponsor"] = df["sponsor"].replace(SPONSOR_ALIASES)
    if interventional_only:
        df = df[df["study_type"] == "INTERVENTIONAL"].reset_index(drop=True)

    df["start_year"] = pd.to_numeric(df["start_year"], errors="coerce").astype("Int64")
    df["enrollment"] = pd.to_numeric(df["enrollment"], errors="coerce")
    df["duration_months"] = pd.to_numeric(df["duration_months"], errors="coerce")
    df["phase"] = pd.Categorical(df["phase"], categories=PHASE_ORDER, ordered=True)
    return df


def quality_report(df):
    """Share of missing values in the fields the analysis depends on.

    A field that is 100% missing usually means the API returned a different
    shape than expected, so the pipeline stops rather than drawing wrong charts.
    """
    key_cols = ["status", "phase", "sponsor", "sponsor_class", "start_date",
                "completion_date", "enrollment", "countries"]
    report = {}
    for col in key_cols:
        series = df[col]
        if col == "countries":
            missing = (series.fillna("") == "").mean()
        else:
            missing = series.isna().mean()
        report[col] = round(float(missing) * 100, 1)
    return report
