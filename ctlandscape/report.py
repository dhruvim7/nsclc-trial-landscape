"""Write reports/numbers.md: every figure's underlying numbers, no interpretation."""

import json

import pandas as pd

from . import analyze as an
from . import settings


def _table(df, index=False):
    if df is None or len(df) == 0:
        return "_No data._\n"
    df = df.reset_index() if index else df
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        cells = []
        for v in row:
            if isinstance(v, float):
                cells.append("" if pd.isna(v) else f"{v:,.1f}".rstrip("0").rstrip("."))
            else:
                cells.append("" if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write(df, quality):
    meta = json.loads(settings.META_FILE.read_text()) if settings.META_FILE.exists() else {}
    h = an.headline(df)
    conc = pd.DataFrame([an.concentration(df, an.PRIOR), an.concentration(df, an.RECENT)])

    parts = [
        f"# Numbers behind the analysis: {settings.CONDITION}\n",
        f"Downloaded {meta.get('downloaded_on', 'n/a')} from ClinicalTrials.gov "
        f"(request mode: {meta.get('request_mode', 'n/a')}; "
        f"{meta.get('records_downloaded', 'n/a')} records of {meta.get('registry_total', 'n/a')} matched). "
        f"Analysis covers {h['trials']:,} interventional trials.\n",
        "## Headline\n",
        f"- Distinct lead sponsors: {h['sponsors']:,}",
        f"- Industry-led share, all years: {h['industry_share_all']}%; trials started {h['recent_span']}: {h['industry_share_recent']}%",
        f"- Currently recruiting: {h['recruiting_now']:,}",
        f"- Finished trials: {h['finished']:,}; terminated or withdrawn: {h['stop_rate']}%",
        f"- Trials matched to at least one mechanism class: {h['with_mechanism']}%\n",
        "## Sanity checks\n",
        ("\n".join(f"- {n}" for n in an.sanity_checks(df)) or "- All headline numbers fall in expected ranges.") + "\n",
        "## Data completeness (% missing)\n",
        _table(pd.DataFrame([quality])),
        "## Trial starts by stage and year\n", _table(an.starts_by_stage(df, settings.FIRST_YEAR), index=True),
        "## Industry share by start year\n", _table(an.industry_share_by_year(df, settings.FIRST_YEAR)),
        "## Industry sponsor concentration\n",
        "HHI = sum of squared % shares of industry trial starts (0-10,000). Known subsidiaries are merged into their parent (see SPONSOR_ALIASES in parse.py).\n",
        _table(conc),
        f"## Top industry sponsors, {h['recent_span']}\n", _table(an.top_industry_sponsors(df)),
        "## Trials by mechanism class\n",
        "growth_pct shown only where the prior period has at least 10 trials.\n",
        _table(an.mechanism_counts(df), index=True),
        f"## Industry share within each mechanism class, {h['recent_span']}\n",
        _table(an.mechanism_industry_share(df)),
        "## Share of trial starts with a site in each location\n",
        _table(an.country_share_by_year(df, settings.FIRST_YEAR)),
        f"## Top countries by trials, {h['recent_span']}\n", _table(an.top_countries(df)),
        "## Stop rate by stage and sponsor type (finished trials)\n", _table(an.stop_rates(df)),
        "## Stated reasons for stopping\n", _table(an.stop_reasons(df), index=True),
        "## Enrollment by stage\n", _table(an.enrollment_by_stage(df)),
        "## Duration of completed trials (months)\n", _table(an.duration_by_stage(df)),
    ]
    settings.REPORT_DIR.mkdir(exist_ok=True)
    path = settings.REPORT_DIR / "numbers.md"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
