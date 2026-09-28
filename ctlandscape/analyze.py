"""Landscape metrics. Every function takes the clean trial table and returns a small DataFrame."""

import re
from datetime import date

import pandas as pd

from .mechanisms import MECHANISM_ORDER
from .parse import PHASE_ORDER, SEP

LAST_FULL_YEAR = date.today().year - 1
RECENT = (LAST_FULL_YEAR - 4, LAST_FULL_YEAR)        # last five full years
PRIOR = (LAST_FULL_YEAR - 9, LAST_FULL_YEAR - 5)     # the five years before that

FINISHED = ["COMPLETED", "TERMINATED", "WITHDRAWN"]
STOPPED = ["TERMINATED", "WITHDRAWN"]

SPONSOR_GROUPS = {
    "INDUSTRY": "Industry",
    "NIH": "NIH / US federal",
    "FED": "NIH / US federal",
    "OTHER_GOV": "Other government",
    "OTHER": "Academic / other",
    "INDIV": "Academic / other",
    "NETWORK": "Academic / other",
}
SPONSOR_GROUP_ORDER = ["Industry", "Academic / other", "NIH / US federal",
                       "Other government", "Unknown"]

STAGES = {
    "Early Phase 1": "Phase 1 (incl. 1/2)",
    "Phase 1": "Phase 1 (incl. 1/2)",
    "Phase 1/2": "Phase 1 (incl. 1/2)",
    "Phase 2": "Phase 2 (incl. 2/3)",
    "Phase 2/3": "Phase 2 (incl. 2/3)",
    "Phase 3": "Phase 3",
    "Phase 4": "Phase 4",
    "No phase": "No phase",
}
STAGE_ORDER = ["Phase 1 (incl. 1/2)", "Phase 2 (incl. 2/3)", "Phase 3", "Phase 4", "No phase"]


def sponsor_group(df):
    return df["sponsor_class"].map(SPONSOR_GROUPS).fillna("Unknown")


def industry_vs_rest(df):
    return df["sponsor_class"].eq("INDUSTRY").map({True: "Industry", False: "Non-industry"})


def year_mask(df, first, last):
    # start_year is a nullable integer; missing years must count as False, not NA
    return df["start_year"].between(first, last).fillna(False).astype(bool)


def in_years(df, span):
    return df[year_mask(df, span[0], span[1])]


def _split(series):
    """Explode a '|'-joined column into one value per row, dropping blanks."""
    out = series.fillna("").astype(str).str.split(SEP).explode().str.strip()
    return out[out != ""]


# --- overview ---------------------------------------------------------------

def headline(df):
    finished = df[df["status"].isin(FINISHED)]
    recent = in_years(df, RECENT)
    return {
        "trials": len(df),
        "sponsors": int(df["sponsor"].nunique()),
        "industry_share_all": round((df["sponsor_class"] == "INDUSTRY").mean() * 100, 1),
        "industry_share_recent": round((recent["sponsor_class"] == "INDUSTRY").mean() * 100, 1)
        if len(recent) else None,
        "recruiting_now": int((df["status"] == "RECRUITING").sum()),
        "finished": len(finished),
        "stop_rate": round(finished["status"].isin(STOPPED).mean() * 100, 1) if len(finished) else None,
        "with_mechanism": round((df["mechanisms"].fillna("") != "").mean() * 100, 1),
        "recent_span": f"{RECENT[0]}-{RECENT[1]}",
        "prior_span": f"{PRIOR[0]}-{PRIOR[1]}",
    }


# --- pipeline shape -----------------------------------------------------------

def starts_by_stage(df, first_year):
    sub = df[year_mask(df, first_year, LAST_FULL_YEAR)].copy()
    sub["stage"] = sub["phase"].astype(str).map(STAGES)
    table = pd.crosstab(sub["start_year"], sub["stage"])
    return table.reindex(columns=[s for s in STAGE_ORDER if s in table.columns], fill_value=0)


def industry_share_by_year(df, first_year):
    sub = df[year_mask(df, first_year, LAST_FULL_YEAR)]
    out = sub.groupby("start_year").agg(
        trials=("nct_id", "size"),
        industry=("sponsor_class", lambda s: (s == "INDUSTRY").sum()),
    )
    out["industry_pct"] = (out["industry"] / out["trials"] * 100).round(1)
    return out.reset_index()


# --- competition ------------------------------------------------------------

def top_industry_sponsors(df, span=RECENT, n=12):
    sub = in_years(df, span)
    sub = sub[sub["sponsor_class"] == "INDUSTRY"]
    counts = sub["sponsor"].value_counts()
    out = counts.head(n).rename_axis("sponsor").reset_index(name="trials")
    out["share_pct"] = (out["trials"] / counts.sum() * 100).round(1)
    return out


def concentration(df, span):
    """Top-5 share and Herfindahl-Hirschman index of industry trial starts.

    HHI = sum of squared percentage shares (0-10,000). Known subsidiaries are merged first
    (SPONSOR_ALIASES in parse.py); other name variants may remain.
    """
    sub = in_years(df, span)
    counts = sub.loc[sub["sponsor_class"] == "INDUSTRY", "sponsor"].value_counts()
    if counts.empty:
        return {"span": f"{span[0]}-{span[1]}", "industry_trials": 0,
                "sponsors": 0, "top5_pct": None, "hhi": None}
    shares = counts / counts.sum() * 100
    return {
        "span": f"{span[0]}-{span[1]}",
        "industry_trials": int(counts.sum()),
        "sponsors": int(counts.size),
        "top5_pct": round(float(shares.head(5).sum()), 1),
        "hhi": round(float((shares ** 2).sum())),
    }


def mechanism_counts(df):
    """Trials per mechanism class, prior five years vs recent five years."""
    rows = []
    for label, span in (("prior", PRIOR), ("recent", RECENT)):
        sub = in_years(df, span)
        counts = _split(sub["mechanisms"]).value_counts()
        for mech in MECHANISM_ORDER:
            rows.append({"mechanism": mech, "period": label, "trials": int(counts.get(mech, 0))})
    out = pd.DataFrame(rows).pivot(index="mechanism", columns="period", values="trials")
    out = out.reindex(MECHANISM_ORDER).fillna(0).astype(int)
    out["change"] = out["recent"] - out["prior"]
    out["growth_pct"] = [
        round((r - p) / p * 100) if p >= 10 else None for p, r in zip(out["prior"], out["recent"])
    ]
    return out[["prior", "recent", "change", "growth_pct"]].sort_values("recent", ascending=False)


def mechanism_industry_share(df, span=RECENT):
    sub = in_years(df, span)[["mechanisms", "sponsor_class"]].copy()
    sub["mechanism"] = sub["mechanisms"].fillna("").str.split(SEP)
    sub = sub.explode("mechanism")
    sub = sub[sub["mechanism"] != ""]
    out = sub.groupby("mechanism").agg(
        trials=("sponsor_class", "size"),
        industry_pct=("sponsor_class", lambda s: round((s == "INDUSTRY").mean() * 100, 1)),
    )
    return out.sort_values("trials", ascending=False).reset_index()


# --- geography ----------------------------------------------------------------

def country_share_by_year(df, first_year, countries=("United States", "China")):
    sub = df[year_mask(df, first_year, LAST_FULL_YEAR)]
    sub = sub[sub["n_countries"] > 0]          # site list present
    out = pd.DataFrame({"start_year": sorted(sub["start_year"].dropna().unique())})
    for c in countries:
        has = sub["countries"].fillna("").str.split(SEP).apply(lambda xs: c in xs)
        share = has.groupby(sub["start_year"]).mean() * 100
        out[c] = out["start_year"].map(share).round(1)
    multi = (sub["n_countries"] > 1).groupby(sub["start_year"]).mean() * 100
    out["Multi-country"] = out["start_year"].map(multi).round(1)
    return out


def top_countries(df, span=RECENT, n=12):
    sub = in_years(df, span)
    counts = _split(sub["countries"]).value_counts().head(n)
    return counts.rename_axis("country").reset_index(name="trials")


# --- execution risk -------------------------------------------------------------

def stop_rates(df):
    """(Terminated + withdrawn) / finished trials, by development stage and sponsor group."""
    sub = df[df["status"].isin(FINISHED)].copy()
    sub["stage"] = sub["phase"].astype(str).map(STAGES)
    sub["group"] = industry_vs_rest(sub)
    sub["stopped"] = sub["status"].isin(STOPPED)
    out = sub.groupby(["stage", "group"]).agg(finished=("stopped", "size"), stopped=("stopped", "sum"))
    out["stop_pct"] = (out["stopped"] / out["finished"] * 100).round(1)
    out = out.reset_index()
    out["stage"] = pd.Categorical(out["stage"], categories=STAGE_ORDER, ordered=True)
    return out.sort_values(["stage", "group"]).reset_index(drop=True)


REASON_RULES = [
    ("Slow or low accrual", r"accru|enrol|recruit|participant|patient.{0,20}(identif|availab|eligib)"),
    ("Business / sponsor decision", r"business|sponsor decision|strateg|portfolio|priorit|commercial|company decision|development program"),
    ("Efficacy / futility", r"futil|efficacy|interim analys|lack of (benefit|activity|response)|ineffective|endpoint"),
    ("Safety / toxicity", r"safety|toxicit|adverse|side effect"),
    ("Funding", r"fund|financ|budget|grant"),
    ("Investigator / site", r"\bpi\b|investigator|left the institution|relocat|site closure"),
    ("COVID-19", r"covid|pandemic|sars-cov"),
    ("Drug supply / regulatory", r"supply|availability of (drug|study drug)|manufactur|regulator|approv"),
]


def reason_category(text):
    if not isinstance(text, str) or not text.strip():
        return "Not reported"
    lowered = text.lower()
    for label, pattern in REASON_RULES:
        if re.search(pattern, lowered):
            return label
    return "Other"


def stop_reasons(df):
    sub = df[df["status"].isin(STOPPED)].copy()
    sub["reason"] = sub["why_stopped"].map(reason_category)
    sub["group"] = industry_vs_rest(sub)
    out = pd.crosstab(sub["reason"], sub["group"])
    out["total"] = out.sum(axis=1)
    return out.sort_values("total", ascending=False)


# --- operations ----------------------------------------------------------------

def enrollment_by_stage(df):
    sub = df[df["enrollment"].between(1, 20000).fillna(False).astype(bool)].copy()
    sub["stage"] = sub["phase"].astype(str).map(STAGES)
    sub["group"] = industry_vs_rest(sub)
    out = sub.groupby(["stage", "group"])["enrollment"].agg(
        n="size", median="median",
        q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75),
    ).reset_index()
    out = out[out["stage"] != "No phase"]
    out["stage"] = pd.Categorical(out["stage"], categories=STAGE_ORDER, ordered=True)
    return out.sort_values(["stage", "group"]).reset_index(drop=True)


def duration_by_stage(df):
    """Start-to-completion months for completed trials with an ACTUAL completion date.

    If the download carried no date types at all, completed trials are used
    as they are and the output is flagged.
    """
    done = df[(df["status"] == "COMPLETED") & df["duration_months"].between(1, 240).fillna(False).astype(bool)].copy()
    types_present = done["completion_date_type"].notna().any()
    if types_present:
        done = done[done["completion_date_type"] != "ESTIMATED"]
    done["stage"] = done["phase"].astype(str).map(STAGES)
    out = done.groupby("stage")["duration_months"].agg(
        n="size", median="median",
        q1=lambda s: s.quantile(0.25), q3=lambda s: s.quantile(0.75),
    ).reindex([s for s in STAGE_ORDER if s != "No phase"]).dropna(subset=["n"]).reset_index()
    out.attrs["actual_dates_only"] = bool(types_present)
    return out


def sanity_checks(df):
    """Flag results that fall outside published ranges, which usually means a data problem.

    Reference points: about 12% of registered trials with results were terminated
    (Williams et al., PLoS One 2015); up to roughly a quarter of trials stop early
    in broader estimates. Registry stop rates are descriptive and are not
    probability-of-success figures.
    """
    h = headline(df)
    notes = []
    if h["stop_rate"] is not None and not 3 <= h["stop_rate"] <= 40:
        notes.append(f"Stop rate of {h['stop_rate']}% is outside the 3-40% range usually seen; "
                     "check status handling before quoting it.")
    if not 10 <= h["industry_share_all"] <= 90:
        notes.append(f"Industry share of {h['industry_share_all']}% looks implausible; check sponsor_class.")
    if h["trials"] < 200:
        notes.append(f"Only {h['trials']} trials; the condition query may be too narrow.")
    unmatched = 100 - h["with_mechanism"]
    if unmatched > 80:
        notes.append(f"{unmatched:.0f}% of trials match no mechanism class; the drug dictionary may need extending.")
    return notes
