"""Static charts for the README and memo."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import analyze as an
from . import settings

INK = "#1f2933"
MUTED = "#7b8794"
INDUSTRY = "#1d4e89"
OTHER = "#9fb3c8"
ACCENT = "#c05621"
STAGE_COLORS = ["#9fb3c8", "#5f8dbf", "#1d4e89", "#3e7c59", "#d9d9d9"]

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "legend.frameon": False,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
})


def _finish(fig, ax, name, note):
    fig.text(0.01, 0.0, note, fontsize=8, color=MUTED, ha="left", va="top")
    settings.FIG_DIR.mkdir(exist_ok=True)
    path = settings.FIG_DIR / name
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def stage_mix(df, note):
    table = an.starts_by_stage(df, settings.FIRST_YEAR)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bottom = np.zeros(len(table))
    for col, color in zip(table.columns, STAGE_COLORS):
        ax.bar(table.index.astype(int), table[col], bottom=bottom, color=color, label=col, width=0.8)
        bottom += table[col].to_numpy()
    ax.set_title("Interventional trial starts per year, by development stage")
    ax.set_ylabel("Trials started")
    ax.set_ylim(0, bottom.max() * 1.2)
    ax.legend(ncol=5, fontsize=8, loc="upper left")
    return _finish(fig, ax, "01_starts_by_stage.png", note)


def industry_share(df, note):
    data = an.industry_share_by_year(df, settings.FIRST_YEAR)
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(data["start_year"].astype(int), data["industry_pct"], color=INDUSTRY, marker="o", lw=2)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of trial starts with an industry lead sponsor")
    ax.set_title("Industry share of new trials")
    return _finish(fig, ax, "02_industry_share.png", note)


def top_sponsors(df, note):
    data = an.top_industry_sponsors(df)
    conc = an.concentration(df, an.RECENT)
    fig, ax = plt.subplots(figsize=(8, 5))
    names = [s if len(s) <= 40 else s[:38] + "..." for s in data["sponsor"]]
    ax.barh(names[::-1], data["trials"][::-1], color=INDUSTRY)
    ax.set_xlabel(f"Industry-sponsored trials started {conc['span']}")
    ax.set_title("Largest industry sponsors")
    if conc["top5_pct"] is not None:
        ax.text(0.98, 0.04, f"Top-5 share: {conc['top5_pct']}%\nHHI: {conc['hhi']:,}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=INK)
    return _finish(fig, ax, "03_top_industry_sponsors.png", note)


def mechanisms(df, note):
    data = an.mechanism_counts(df)
    data = data[(data["prior"] + data["recent"]) > 0].sort_values("recent")
    y = np.arange(len(data))
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(y - 0.2, data["prior"], height=0.4, color=OTHER, label=f"{an.PRIOR[0]}-{an.PRIOR[1]}")
    ax.barh(y + 0.2, data["recent"], height=0.4, color=INDUSTRY, label=f"{an.RECENT[0]}-{an.RECENT[1]}")
    ax.set_yticks(y, data.index)
    ax.set_xlabel("Trials started (a trial can test more than one class)")
    ax.set_title("Where the pipeline is crowding: trials by mechanism class")
    ax.legend(loc="lower right")
    return _finish(fig, ax, "04_mechanism_classes.png", note)


def geography(df, note):
    data = an.country_share_by_year(df, settings.FIRST_YEAR)
    fig, ax = plt.subplots(figsize=(9, 4))
    styles = {"United States": (INDUSTRY, "-"), "China": (ACCENT, "-"), "Multi-country": (MUTED, "--")}
    for col, (color, ls) in styles.items():
        ax.plot(data["start_year"].astype(int), data[col], color=color, ls=ls, lw=2, label=col)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of trial starts")
    ax.set_title("Where trials run: share with at least one site in each location")
    ax.legend()
    return _finish(fig, ax, "05_geography.png", note)


def stop_rates(df, note):
    data = an.stop_rates(df)
    data = data[data["stage"] != "No phase"]
    stages = [s for s in an.STAGE_ORDER if s in set(data["stage"].astype(str))]
    x = np.arange(len(stages))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for offset, group, color in ((-0.2, "Industry", INDUSTRY), (0.2, "Non-industry", OTHER)):
        sub = data[data["group"] == group].set_index(data[data["group"] == group]["stage"].astype(str))
        vals = [sub["stop_pct"].get(s, np.nan) for s in stages]
        ax.bar(x + offset, vals, width=0.4, color=color, label=group)
    ax.set_xticks(x, stages)
    ax.set_ylabel("% of finished trials terminated or withdrawn")
    ax.set_title("Early stopping by stage and sponsor type")
    ax.set_ylim(0, np.nanmax(data["stop_pct"].to_numpy(dtype=float)) * 1.25)
    ax.legend(ncol=2, loc="upper left")
    return _finish(fig, ax, "06_stop_rates.png", note)


def stop_reasons(df, note):
    data = an.stop_reasons(df)
    missing = int(data["total"].get("Not reported", 0))
    data = data.drop(index="Not reported", errors="ignore").sort_values("total")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    left = np.zeros(len(data))
    for group, color in (("Industry", INDUSTRY), ("Non-industry", OTHER)):
        if group in data.columns:
            ax.barh(data.index, data[group], left=left, color=color, label=group)
            left += data[group].to_numpy()
    ax.set_xlabel("Terminated or withdrawn trials")
    ax.set_title("Stated reasons for stopping")
    ax.legend(loc="lower right")
    note = note + f"  Reasons classified by keyword; {missing:,} stopped trials gave no reason."
    return _finish(fig, ax, "07_stop_reasons.png", note)


def enrollment(df, note):
    data = an.enrollment_by_stage(df)
    stages = [s for s in an.STAGE_ORDER if s in set(data["stage"].astype(str))]
    x = np.arange(len(stages))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for offset, group, color in ((-0.2, "Industry", INDUSTRY), (0.2, "Non-industry", OTHER)):
        sub = data[data["group"] == group].set_index(data[data["group"] == group]["stage"].astype(str))
        med = np.array([sub["median"].get(s, np.nan) for s in stages])
        lo = med - np.array([sub["q1"].get(s, np.nan) for s in stages])
        hi = np.array([sub["q3"].get(s, np.nan) for s in stages]) - med
        ax.bar(x + offset, med, width=0.4, color=color, label=group,
               yerr=[lo, hi], capsize=3, ecolor=MUTED)
    ax.set_xticks(x, stages)
    ax.set_ylabel("Planned or actual enrollment (median, IQR)")
    ax.set_title("Trial size by stage")
    ax.set_ylim(0, np.nanmax(data["q3"].to_numpy(dtype=float)) * 1.2)
    ax.legend(ncol=2, loc="upper left")
    return _finish(fig, ax, "08_enrollment.png", note)


def duration(df, note):
    data = an.duration_by_stage(df)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    y = np.arange(len(data))
    ax.barh(y, data["median"], color=INDUSTRY, height=0.55)
    ax.errorbar(data["median"], y, xerr=[data["median"] - data["q1"], data["q3"] - data["median"]],
                fmt="none", ecolor=MUTED, capsize=3)
    ax.set_yticks(y, data["stage"])
    ax.invert_yaxis()
    ax.set_xlabel("Months from start to completion (median, IQR)")
    ax.set_title("How long completed trials took")
    extra = "" if data.attrs.get("actual_dates_only") else "  Date types unavailable; includes estimated dates."
    return _finish(fig, ax, "09_duration.png", note + extra)


def all_figures(df, note):
    makers = [stage_mix, industry_share, top_sponsors, mechanisms, geography,
              stop_rates, stop_reasons, enrollment, duration]
    return [make(df, note) for make in makers]
