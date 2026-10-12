"""Is the growth in volunteer alert starts a change in what is measured at the switch to raion-level alerts?

    python -m src.check_measurement            # pinned dataset commit
    python -m src.check_measurement --latest

Why this exists: the volunteer file has 2.5 times more alert starts in Sep 2026 than in an average month
of H1 2025, while the number of regions with an alert start per day stays between 16 and 19 until Aug 2026. If one real
alert were split into several starts after the official switch to raion-level alerts, starts per active
region-day would jump at the switch and the series would change meaning.

Rule fixed before looking at the numbers:
  * the switch day is derived from the official file: the first day from which official oblast-level rows
    stay below 10 a day for 14 days in a row (searched from 2025-08-01);
  * value(window) = alert starts / (region, day) pairs with at least one start, over a 90-day window;
  * ratio(C) = value(90 days from C) / value(90 days before C);
  * ratio at the switch day is compared with the ratio at 28 placebo days (1st of every month, 2024-04
    to 2026-07). The switch counts as a jump if its ratio is among the top 3 of the 29 ratios.

Writes reports/volunteer_measurement_check.md, reports/volunteer_monthly_diagnostics.csv and
reports/fig_volunteer_measurement.png.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, plotting
from .data import download, load_raw, resolve_commit
from .inspect_data import Report
from .target import clean_events, kyiv_day, last_complete_day, load_events

T0 = pd.Timestamp("1970-01-01", tz="UTC")
SWITCH_SEARCH_FROM = "2025-08-01"
LOW_ROWS, LOOK_DAYS = 10, 14
PLACEBO_FIRST, PLACEBO_LAST = "2024-04-01", "2026-07-01"
TOP_K = 3


def official_daily_by_level(path: Path) -> pd.DataFrame:
    """Official alert rows per Kyiv day and level, exact duplicate rows removed (cross-check only)."""
    raw = load_raw(path)
    d = raw.loc[~raw.duplicated()]
    day = kyiv_day(pd.to_datetime(d["started_at"], utc=True, format="ISO8601"))
    by_level = pd.crosstab(day, d["level"])
    return by_level.reindex(pd.date_range(by_level.index.min(), by_level.index.max(), freq="D"), fill_value=0)


def find_switch_day(by_level: pd.DataFrame) -> pd.Timestamp:
    obl = by_level["oblast"]
    fwd_max = obl.rolling(LOOK_DAYS).max().shift(-(LOOK_DAYS - 1))  # max over [d, d + 13]
    ok = fwd_max[(fwd_max.index >= pd.Timestamp(SWITCH_SEARCH_FROM)) & (fwd_max < LOW_ROWS)]
    if ok.empty:
        raise ValueError("no day found from which official oblast-level rows stay low; look at reports/data_check.md")
    return ok.index.min()


def prepare(ev: pd.DataFrame, last_day: pd.Timestamp) -> pd.DataFrame:
    """Add Kyiv day, month, duration and a flag for starts that follow the previous alert within minutes."""
    e = ev.assign(day=kyiv_day(ev["started_at"]))
    e = e.loc[e["day"] <= last_day].sort_values(["region", "started_at"], kind="stable").reset_index(drop=True)
    e["month"] = e["day"].dt.to_period("M")
    start_s = (e["started_at"] - T0).dt.total_seconds()
    end_s = (e["finished_at"] - T0).dt.total_seconds()
    # latest end among the region's earlier alerts, over the whole history (does not reset at month ends)
    prev_end = end_s.groupby(e["region"]).transform(lambda s: s.cummax().shift(1))
    e["gap_min"] = (start_s - prev_end) / 60  # minutes since the latest end among the region's earlier alerts
    e["rapid"] = e["gap_min"] <= config.RAPID_RESTART_MIN
    e["duration_min"] = (end_s - start_s) / 60
    return e


def monthly_table(e: pd.DataFrame, by_level: pd.DataFrame) -> pd.DataFrame:
    g = e.groupby("month")
    regions_per_day = e.groupby(["month", "day"])["region"].nunique().groupby("month").mean()
    non_naive = e.loc[~e["naive"]]
    hours = (e["duration_min"].clip(upper=24 * 60) / 60).groupby(e["month"]).sum()
    t = pd.DataFrame({
        "days": g["day"].nunique(),
        "starts": g.size(),
        "active_regions": g["region"].nunique(),
        "active_region_days": e.drop_duplicates(["region", "day"]).groupby("month").size(),
        "regions_with_start_per_day": regions_per_day,
        "median_duration_min": non_naive.groupby("month")["duration_min"].median(),
        "rapid_restart_share": g["rapid"].mean(),
        "naive_share": g["naive"].mean(),
        "alert_hours": hours,
    })
    t["starts_per_active_region"] = t["starts"] / t["active_regions"]
    t["starts_per_active_region_day"] = t["starts"] / t["active_region_days"]
    off = by_level.groupby(by_level.index.to_period("M")).sum()
    t["official_oblast_rows"] = off["oblast"]
    t["official_raion_hromada_rows"] = off["raion"] + off["hromada"]
    return t.loc[t.index >= pd.Period(config.DIAG_FIRST_MONTH, "M")]


def switch_test(e: pd.DataFrame, switch_day: pd.Timestamp) -> dict:
    daily = e.groupby("day").agg(starts=("region", "size"), active=("region", "nunique"))
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"), fill_value=0)
    win, one = pd.Timedelta(days=config.SWITCH_WINDOW_DAYS), pd.Timedelta(days=1)

    def value(a, b) -> float:
        w = daily.loc[a:b]
        return w["starts"].sum() / w["active"].sum()

    def ratio(c) -> tuple[float, float, float]:
        c = pd.Timestamp(c)
        pre, post = value(c - win, c - one), value(c, c + win - one)
        return pre, post, post / pre

    pre, post, r = ratio(switch_day)
    placebo = pd.Series({d: ratio(d)[2] for d in pd.date_range(PLACEBO_FIRST, PLACEBO_LAST, freq="MS")})
    n_ge = int((placebo >= r).sum())
    return {"pre": pre, "post": post, "ratio": r, "placebo": placebo, "n_placebo_ge": n_ge,
            "rank": n_ge + 1, "of": len(placebo) + 1, "jump": n_ge + 1 <= TOP_K}


MERGE_GAPS = (10, 30, 60, 120)
MERGE_PERIODS = {"2025 H1": ("2025-01-01", "2025-06-30"), "2025 Q4": ("2025-10-01", "2025-12-31"),
                 "Aug-Sep 2026": ("2026-08-01", "2026-09-30")}


def merge_sensitivity(e: pd.DataFrame) -> pd.DataFrame:
    """Starts per active region-day if a start that comes within G minutes of the end of the region's previous alert
    is counted as part of that alert. The number of (region, day) pairs with a start is left as it is."""
    out = {}
    for name, (a, b) in MERGE_PERIODS.items():
        w = e.loc[(e["day"] >= pd.Timestamp(a)) & (e["day"] <= pd.Timestamp(b))]
        region_days = len(w.drop_duplicates(["region", "day"]))
        col = {"rows as published": len(w) / region_days}
        for g in MERGE_GAPS:
            col[f"merged if gap <= {g} min"] = int((~(w["gap_min"] <= g)).sum()) / region_days
        out[name] = col
    t = pd.DataFrame(out)
    t["Aug-Sep 2026 / 2025 H1"] = t["Aug-Sep 2026"] / t["2025 H1"]
    return t


def plot(tab: pd.DataFrame, switch_day: pd.Timestamp, path) -> None:
    x = tab.index.to_timestamp()
    panels = [
        ("alert starts per day (monthly mean)", tab["starts"] / tab["days"]),
        ("regions with an alert start per day (monthly mean)", tab["regions_with_start_per_day"]),
        ("alert starts per active region-day", tab["starts_per_active_region_day"]),
    ]
    fig, axes = plotting.new_figure(len(panels), height_per_row=2.3)
    for ax, (title, series) in zip(axes, panels):
        ax.plot(x, series, color=plotting.BLUE, lw=1.3, marker="o", ms=3)
        ax.axvline(switch_day, color=plotting.INK_2, lw=0.8, ls=(0, (4, 3)))
        ax.set_title(title, loc="left", color=plotting.INK, fontsize=10)
        ax.set_ylim(bottom=0)
    axes[0].annotate(f"{switch_day:%Y-%m-%d}: official oblast-level rows drop", xy=(switch_day, 1),
                     xycoords=("data", "axes fraction"), xytext=(5, -2), textcoords="offset points",
                     va="top", fontsize=8, color=plotting.INK_2)
    plotting.save(fig, path, "Volunteer file: did what is counted change at the switch? "
                             "(24 regions; last month partial)")


def run(volunteer: Path, official: Path, commit: str) -> dict:
    ev, _ = clean_events(load_events(volunteer))
    last_day = last_complete_day(ev)
    by_level = official_daily_by_level(official)
    switch_day = find_switch_day(by_level)
    e = prepare(ev, last_day)
    tab = monthly_table(e, by_level)
    test = switch_test(e, switch_day)
    sens = merge_sensitivity(e)

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    tab.to_csv(config.REPORTS_DIR / "volunteer_monthly_diagnostics.csv", encoding="utf-8")
    plot(tab, switch_day, config.REPORTS_DIR / "fig_volunteer_measurement.png")

    rep = Report()
    rep.add("# Check: does the volunteer series change meaning at the switch to raion-level alerts?")
    rep.add(f"volunteer file @ {commit}; Luhanska excluded; last complete day {last_day:%Y-%m-%d}; "
            "official file used only to date the switch.")
    rep.add(f"switch day derived from the official file: {switch_day:%Y-%m-%d} (first day from which "
            f"oblast-level rows stay below {LOW_ROWS} a day for {LOOK_DAYS} days, searched from {SWITCH_SEARCH_FROM}).")
    rep.add("\nColumns: starts = alert starts in the month; active_region_days = (region, day) pairs with at least "
            "one start; rapid_restart_share = starts within "
            f"{config.RAPID_RESTART_MIN} min of the end of an earlier alert of the same region (or overlapping it); "
            "naive_share = rows whose end is a 30-minute placeholder; alert_hours = sum of durations, each capped "
            "at 24 h; official_* = official rows per month (duplicates removed), for context. "
            f"The last month ({tab.index[-1]}) has {int(tab['days'].iloc[-1])} days.")
    show = tab.round({"regions_with_start_per_day": 1, "median_duration_min": 1, "rapid_restart_share": 3,
                      "naive_share": 3, "alert_hours": 0, "starts_per_active_region": 1,
                      "starts_per_active_region_day": 2})
    rep.add("\n## Monthly diagnostics\n")
    rep.table(show)

    full = tab.iloc[:-1]  # leave out the partial last month when ranking jumps
    chg = np.log(full["starts_per_active_region_day"]).diff().dropna()
    top = chg.abs().sort_values(ascending=False).head(5)
    rep.add("\n## Largest month-to-month changes in starts per active region-day (partial month left out)\n")
    rep.table(pd.DataFrame({"change_%": (np.exp(chg[top.index]) - 1).mul(100).round(1)}))

    rep.add("\n## Switch test\n")
    p = test["placebo"]
    rep.add(f"starts per active region-day: {test['pre']:.3f} in the 90 days before {switch_day:%Y-%m-%d}, "
            f"{test['post']:.3f} in the 90 days from it; ratio {test['ratio']:.3f}.")
    rep.add(f"placebo ratios (28 dates, 1st of each month): min {p.min():.3f}, median {p.median():.3f}, "
            f"max {p.max():.3f}; {test['n_placebo_ge']} of them are >= the switch ratio, so the switch ranks "
            f"{test['rank']} of {test['of']} (rule: a jump if rank <= {TOP_K}) -> "
            f"{'JUMP' if test['jump'] else 'no jump'}.")
    rep.add("placebo ratios by date:")
    rep.table(p.round(3).rename(lambda d: f"{d:%Y-%m-%d}"))
    rep.add("\n## Sensitivity: how much of the rise is carried by alerts that follow each other closely\n")
    rep.add("Starts per active region-day when a start that comes within G minutes of the end of the region's previous "
            "alert counts as part of that alert. The number of (region, day) pairs with a start is not changed.")
    rep.table(sens.round(2))
    rep.save(config.REPORTS_DIR / "volunteer_measurement_check.md")
    return {"switch_day": switch_day, "table": tab, "test": test, "sensitivity": sens}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Check whether the volunteer series changes meaning at the switch")
    parser.add_argument("--latest", action="store_true", help="use the newest dataset commit")
    args = parser.parse_args(argv)
    commit, _ = resolve_commit(args.latest)
    run(download(config.VOLUNTEER_FILE, commit), download(config.OFFICIAL_FILE, commit), commit)


if __name__ == "__main__":
    main()
