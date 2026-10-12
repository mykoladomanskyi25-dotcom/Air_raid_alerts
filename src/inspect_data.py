"""Step 1: verify the raw data before any modelling decision.

Run from the project root:
    python -m src.inspect_data            # pinned dataset commit (config.DATASET_COMMIT)
    python -m src.inspect_data --latest   # newest commit of the dataset repo

Prints the report and saves it to reports/data_check.md, together with
reports/monthly_counts_by_level.csv, reports/daily_counts_by_level.csv and
reports/fig_daily_counts_by_level.png. Nothing is written back to the data: exact duplicate
rows are counted, and the tables from section 3 on show the data with the repeated copies
removed so that they are not counted twice.
"""
from __future__ import annotations

import argparse
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402
from .data import download, load_raw, resolve_commit, write_snapshot  # noqa: E402

REQUIRED = ["oblast", "level", "started_at", "finished_at"]
KEY_COLS = ["oblast", "raion", "hromada", "level", "started_at"]

# Reference palette (light mode): categorical slots 1-3 and chart chrome.
LEVEL_COLORS = {"oblast": "#2a78d6", "raion": "#eb6834", "hromada": "#1baf7a"}
SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


class Report:
    """Print each block and keep it for reports/data_check.md."""

    def __init__(self) -> None:
        self.blocks: list[str] = []

    def add(self, text: str) -> None:
        print(text)
        self.blocks.append(text)

    def section(self, title: str) -> None:
        self.add(f"\n## {title}\n")

    def table(self, obj) -> None:
        self.add("```\n" + obj.to_string() + "\n```")

    def save(self, path) -> None:
        path.write_text("\n".join(self.blocks) + "\n", encoding="utf-8")


def to_kyiv_naive(ts: pd.Series) -> pd.Series:
    """UTC timestamps -> Kyiv wall-clock time without tz info (for day/month labels)."""
    return ts.dt.tz_convert(config.TZ).dt.tz_localize(None)


def parse_times(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    for col in ("started_at", "finished_at"):
        df[col] = pd.to_datetime(raw[col], utc=True, format="ISO8601", errors="coerce")
    return df


def raw_view(rep: Report, raw: pd.DataFrame) -> None:
    rep.section("1. Raw view (every column read as text)")
    rep.add(f"shape: {raw.shape}")
    rep.add(f"columns: {list(raw.columns)}")
    rep.table(raw.dtypes)
    rep.add("head(5):")
    rep.table(raw.head())
    rep.add("tail(5):")
    rep.table(raw.tail())
    if "started_at" in raw.columns:
        picks = [0, len(raw) // 2, len(raw) - 1]
        rep.add("raw started_at strings (first, middle, last row): "
                + ", ".join(repr(raw["started_at"].iloc[i]) for i in picks))
    if "level" in raw.columns:
        rep.add("empty values per column, by level:")
        rep.table(raw.isna().groupby(raw["level"], dropna=False).sum())
    else:
        rep.add("empty values per column:")
        rep.table(raw.isna().sum())
    if "source" in raw.columns:
        rep.add("source value counts:")
        rep.table(raw["source"].value_counts(dropna=False))


def describe_duplicates(rep: Report, raw: pd.DataFrame, df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Count exact duplicate rows; return (mask of repeated copies, repeated copies per month)."""
    rep.section("2. Duplicates, coverage, durations")
    dup = raw.duplicated()
    key = [c for c in KEY_COLS if c in raw.columns]
    rep.add(f"exact duplicate rows (second and later copies): {int(dup.sum())} of {len(raw)} ({dup.mean():.1%}); "
            f"duplicates on {key}: {int(raw.duplicated(subset=key).sum())}")
    month = to_kyiv_naive(df["started_at"]).dt.to_period("M").rename("month")
    per_month = month[dup].value_counts().sort_index().rename("repeated_copies_removed")
    if dup.any():
        pos = raw.index[dup]
        st = df.loc[dup, "started_at"]
        rep.add(f"repeated copies sit at file rows {pos.min()} .. {pos.max()} and cover started_at "
                f"{st.min():%Y-%m-%d} .. {st.max():%Y-%m-%d}")
        share = (per_month / month.value_counts().reindex(per_month.index)).round(2).rename("share_of_month_rows")
        rep.add("repeated copies per month (Kyiv time of start):")
        rep.table(pd.concat([per_month, share], axis=1))
    return dup, per_month


def coverage(rep: Report, raw: pd.DataFrame, df: pd.DataFrame, d: pd.DataFrame) -> None:
    """Time range, empty values and durations. `d` is `df` without the repeated copies."""
    s, f = df["started_at"], df["finished_at"]
    rep.add(f"parsed dtypes: started_at {s.dtype}, finished_at {f.dtype}")
    rows = {}
    for col in ("started_at", "finished_at"):
        ts = df[col]
        rows[col] = {
            "min_utc": ts.min(),
            "max_utc": ts.max(),
            "min_kyiv": ts.min().tz_convert(config.TZ),
            "max_kyiv": ts.max().tz_convert(config.TZ),
            "empty": int(raw[col].isna().sum()),
            "unparseable": int((ts.isna() & raw[col].notna()).sum()),
        }
    rep.table(pd.DataFrame(rows).T)

    dur_min = (d["finished_at"] - d["started_at"]).dt.total_seconds() / 60
    rep.add("duration in minutes (finished_at - started_at), repeated copies removed:")
    rep.table(dur_min.describe(percentiles=[0.01, 0.5, 0.9, 0.99]).round(1))
    rep.add(f"duration <= 0: {int((dur_min <= 0).sum())}; > 24 h: {int((dur_min > 24 * 60).sum())}; "
            f"> 7 days: {int((dur_min > 7 * 24 * 60).sum())}")
    show = [c for c in ("oblast", "raion", "hromada", "level", "started_at", "finished_at") if c in d.columns]
    rep.add("10 longest alerts (repeated copies removed):")
    rep.table(d.assign(hours=(dur_min / 60).round(1)).nlargest(10, "hours")[show + ["hours"]])
    long = d.loc[dur_min > 24 * 60]
    rep.add("alerts longer than 24 h, by oblast and level:")
    rep.table(pd.crosstab(long["oblast"], long["level"], margins=True))
    if f.isna().any():
        rep.add("rows with empty or unparseable finished_at (up to 10):")
        rep.table(df.loc[f.isna(), show].head(10))


def values(rep: Report, d: pd.DataFrame) -> None:
    rep.section("3. Values: alert levels and region names (repeated copies removed)")
    rep.add("level value counts:")
    rep.table(d["level"].value_counts(dropna=False))
    day = to_kyiv_naive(d["started_at"]).dt.normalize().rename("day")
    per = (d.assign(day=day)
             .groupby("oblast", dropna=False)
             .agg(rows=("level", "size"), first_seen=("day", "min"), last_seen=("day", "max")))
    per["first_seen"] = per["first_seen"].dt.strftime("%Y-%m-%d")
    per["last_seen"] = per["last_seen"].dt.strftime("%Y-%m-%d")
    per = per.join(pd.crosstab(d["oblast"], d["level"]))
    rep.add(f"{d['oblast'].nunique()} distinct oblast values "
            "(rows, first/last day seen in Kyiv time, rows per level):")
    rep.table(per)
    for col in ("raion", "hromada"):
        if col in d.columns:
            rep.add(f"distinct {col} values: {d[col].nunique()}")


def plot_daily_by_level(daily: pd.DataFrame, path) -> None:
    """Small multiples: one panel per alert level, shared time axis, own y-axis each."""
    last = daily.loc[daily.index > daily.index.max() - pd.Timedelta(days=540)]
    levels = [c for c in daily.columns if c != "total"]
    fig, axes = plt.subplots(len(levels), 1, figsize=(11, 2.4 * len(levels)), sharex=True,
                             squeeze=False, facecolor=SURFACE)
    for ax, level in zip(axes[:, 0], levels):
        ax.set_facecolor(SURFACE)
        ax.plot(last.index, last[level], color=LEVEL_COLORS.get(level, MUTED), lw=1.1)
        ax.set_title(f"{level}-level alert rows per day", loc="left", color=INK, fontsize=10)
        ax.set_ylim(bottom=0)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=8, labelcolor=INK_2)
    fig.suptitle("Official alert rows per day by level, last 18 months "
                 "(repeated copies removed; Kyiv date of start; separate y-axis per panel)",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)


def collapse_test(rep: Report, d: pd.DataFrame, dup_per_month: pd.Series) -> None:
    rep.section("4. Collapse test: alert rows by level over time (repeated copies removed; Kyiv time of start)")
    local = to_kyiv_naive(d["started_at"])
    month = local.dt.to_period("M").rename("month")
    monthly = pd.crosstab(month, d["level"])
    monthly["total"] = monthly.sum(axis=1)
    monthly = monthly.join(dup_per_month).fillna(0).astype(int)
    monthly.to_csv(config.REPORTS_DIR / "monthly_counts_by_level.csv")
    rep.add("rows per month by level, last 18 months (last month partial; "
            "full table: reports/monthly_counts_by_level.csv):")
    rep.table(monthly.tail(18))

    day = local.dt.normalize().rename("day")
    daily = pd.crosstab(day, d["level"])
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), freq="D"), fill_value=0)
    daily.index.name = "day"
    daily["total"] = daily.sum(axis=1)
    daily.to_csv(config.REPORTS_DIR / "daily_counts_by_level.csv")
    zero_days = daily.index[daily["total"] == 0]
    rep.add(f"days with zero alert rows at all levels, {daily.index.min():%Y-%m-%d} .. "
            f"{daily.index.max():%Y-%m-%d}: {len(zero_days)}")
    if len(zero_days):
        shown = zero_days[-30:]
        rep.add("  " + ", ".join(f"{x:%Y-%m-%d}" for x in shown)
                + (" (last 30 shown)" if len(zero_days) > 30 else ""))
    rep.add("rows per day by level, last 60 days (full table: reports/daily_counts_by_level.csv):")
    last60 = daily.tail(60).copy()
    last60.index = last60.index.strftime("%Y-%m-%d %a")
    rep.table(last60)

    if "oblast" in set(d["level"].dropna()):
        not_oblast = (d["level"] != "oblast").rename("not_oblast_level")
        share = pd.crosstab(d["oblast"], month, values=not_oblast, aggfunc="mean")
        since_2025 = share.loc[:, share.columns >= pd.Period("2025-01", "M")] >= 0.5
        first50 = since_2025.idxmax(axis=1).where(since_2025.any(axis=1))
        recent = share.loc[:, share.columns >= pd.Period("2025-07", "M")]
        tab = (recent * 100).round().astype("Int64")
        tab.columns = [p.strftime("%y-%m") for p in tab.columns]
        tab["first>=50%"] = [p.strftime("%Y-%m") if isinstance(p, pd.Period) else "-" for p in first50]
        rep.add("% of each oblast's rows that are NOT oblast-level (raion/hromada), by month since 2025-07; "
                "last column = first month since 2025-01 with >= 50%:")
        rep.table(tab)
    else:
        rep.add("level value 'oblast' not found: check section 3 before reading anything into levels.")

    fig_path = config.REPORTS_DIR / "fig_daily_counts_by_level.png"
    plot_daily_by_level(daily, fig_path)
    rep.add(f"figure: {fig_path.relative_to(config.ROOT).as_posix()}")


def stream_gaps(rep: Report, starts: pd.Series, label: str, since: str = "2025-01-01",
                min_hours: float = 8, top: int = 12) -> None:
    """Long silences between consecutive alert starts: a quiet night is short, an outage is long."""
    s = starts.dropna().sort_values()
    s = s[s >= pd.Timestamp(since, tz="UTC")]
    g = pd.DataFrame({
        "gap_hours": (s.diff().dt.total_seconds() / 3600).round(1),
        "last_start_before_gap": s.shift(1).dt.tz_convert(config.TZ).dt.strftime("%Y-%m-%d %H:%M"),
        "next_start_after_gap": s.dt.tz_convert(config.TZ).dt.strftime("%Y-%m-%d %H:%M"),
    })
    big = g[g["gap_hours"] >= min_hours].sort_values("gap_hours", ascending=False)
    rep.add(f"{label}: gaps of >= {min_hours:g} h between consecutive alert starts since {since} "
            f"(Kyiv time): {len(big)}; largest {min(top, len(big))}:")
    rep.table(big.head(top))


def tail_check(rep: Report, d: pd.DataFrame, commit_time: str) -> None:
    rep.section("5. Official file: how fresh and how complete is the tail?")
    commit_kyiv = pd.Timestamp(commit_time).tz_convert(config.TZ)
    last_start = d["started_at"].max().tz_convert(config.TZ)
    last_end = d["finished_at"].max().tz_convert(config.TZ)
    rep.add(f"dataset commit: {commit_time} = {commit_kyiv:%Y-%m-%d %H:%M} Kyiv")
    rep.add(f"official file: latest started_at {last_start:%Y-%m-%d %H:%M} Kyiv, latest finished_at "
            f"{last_end:%Y-%m-%d %H:%M} Kyiv = {(commit_kyiv.date() - last_start.date()).days} days "
            "before the commit date")
    stream_gaps(rep, d["started_at"], "official file")

    day = to_kyiv_naive(d["started_at"]).dt.normalize().rename("day")
    per_day = pd.DataFrame({
        "rows": day.value_counts(),
        "oblasts_with_alerts": d.groupby(day)["oblast"].nunique(),
    }).sort_index()
    per_day = per_day.reindex(pd.date_range(per_day.index.min(), per_day.index.max(), freq="D"), fill_value=0)
    med = per_day["rows"].rolling(28).median().shift(1).rename("prev28_median_rows")
    flag = per_day.join(med).assign(ratio=lambda x: (x["rows"] / x["prev28_median_rows"]).round(2))
    flag = flag.loc["2025-01-01":]
    flag = flag[flag["ratio"] < 0.5]
    flag.index = flag.index.strftime("%Y-%m-%d %a")
    rep.add("days since 2025-01-01 with fewer than half the rows of the previous-28-day median "
            "(outage, or a partial day at the start/end of an outage or of the file):")
    rep.table(flag)
    last7 = per_day.tail(7).copy()
    last7.index = last7.index.strftime("%Y-%m-%d %a")
    rep.add("last 7 days of the official file:")
    rep.table(last7)


def volunteer_check(rep: Report, path, official: pd.DataFrame) -> None:
    rep.section("6. Volunteer file, and how well it matches the official file where they overlap")
    v = load_raw(path)
    rep.add(f"shape: {v.shape}; columns: {list(v.columns)}")
    rep.table(v.head(3))
    missing = [c for c in ("region", "started_at", "finished_at") if c not in v.columns]
    if missing:
        rep.add(f"STOP: expected columns {missing} are missing in the volunteer file")
        return
    s = pd.to_datetime(v["started_at"], utc=True, format="ISO8601", errors="coerce")
    f = pd.to_datetime(v["finished_at"], utc=True, format="ISO8601", errors="coerce")
    bad = int((s.isna() & v["started_at"].notna()).sum())
    rep.add(f"started_at range: {s.min().tz_convert(config.TZ):%Y-%m-%d %H:%M} .. "
            f"{s.max().tz_convert(config.TZ):%Y-%m-%d %H:%M} Kyiv (unparseable: {bad}); "
            f"latest finished_at {f.max().tz_convert(config.TZ):%Y-%m-%d %H:%M} Kyiv")
    rep.add(f"exact duplicate rows: {int(v.duplicated().sum())}; empty values per column: "
            + ", ".join(f"{c}={int(v[c].isna().sum())}" for c in v.columns))

    local = to_kyiv_naive(s)
    month = local.dt.to_period("M").rename("month")
    day = local.dt.normalize().rename("day")
    by_month = pd.DataFrame({"rows": month.value_counts()})
    if "naive" in v.columns:
        naive = v["naive"].str.lower().eq("true")
        by_month["naive_share"] = naive.groupby(month).mean().round(2)
    rep.add("rows per month" + (" and share of 'naive' rows (end unknown, finished_at = started_at + 30 min)"
                                if "naive" in v.columns else "") + ", last 24 months:")
    rep.table(by_month.sort_index().tail(24))
    last14 = pd.DataFrame({"rows": day.value_counts()})
    if "naive" in v.columns:
        last14["naive_rows"] = naive.groupby(day).sum().astype(int)
    rep.add("rows per day, last 14 days (the last day is partial):")
    rep.table(last14.sort_index().tail(14))
    dur_min = (f - s).dt.total_seconds() / 60
    cols = {"all rows": dur_min}
    if "naive" in v.columns:
        cols["not naive"] = dur_min[~naive]
    rep.add("alert duration in minutes (finished_at - started_at):")
    rep.table(pd.DataFrame({k: x.describe(percentiles=[0.01, 0.5, 0.9, 0.99]) for k, x in cols.items()}).round(1))
    rep.add(f"duration <= 0: {int((dur_min <= 0).sum())}; > 24 h: {int((dur_min > 24 * 60).sum())}; "
            f"> 7 days: {int((dur_min > 7 * 24 * 60).sum())}")
    stream_gaps(rep, s, "volunteer file")

    reg = (pd.DataFrame({"region": v["region"], "day": day}).groupby("region")
             .agg(rows=("day", "size"), first_seen=("day", "min"), last_seen=("day", "max")))
    reg["first_seen"] = reg["first_seen"].dt.strftime("%Y-%m-%d")
    reg["last_seen"] = reg["last_seen"].dt.strftime("%Y-%m-%d")
    off_names, vol_names = set(official["oblast"].dropna()), set(v["region"].dropna())
    rep.add(f"{len(vol_names)} volunteer regions. Only in the volunteer file: {sorted(vol_names - off_names)}; "
            f"only in the official file: {sorted(off_names - vol_names)}")
    rep.table(reg)

    # Overlap: do the two sources move together before and after the switch to raion-level alerts?
    o_day = to_kyiv_naive(official["started_at"]).dt.normalize()
    o_regions = official.groupby(o_day)["oblast"].nunique()
    o_rows = o_day.value_counts()
    o_oblast_rows = o_day[official["level"] == "oblast"].value_counts()
    v_regions = v["region"].groupby(day).nunique()
    v_rows = day.value_counts()
    periods = {
        "2024 (before the switch)": ("2024-01-01", "2024-12-31"),
        "2025-01..06 (before the switch)": ("2025-01-01", "2025-06-30"),
        "2026-03-01..08-28 (after the switch, before the outage)": ("2026-03-01", "2026-08-28"),
    }
    out = {}
    for name, (a, b) in periods.items():
        idx = pd.date_range(a, b, freq="D")
        o_r, v_r = o_regions.reindex(idx, fill_value=0), v_regions.reindex(idx, fill_value=0)
        out[name] = {
            "days": len(idx),
            "official rows/day, all levels": round(o_rows.reindex(idx, fill_value=0).mean(), 1),
            "official rows/day, oblast level": round(o_oblast_rows.reindex(idx, fill_value=0).mean(), 1),
            "volunteer rows/day": round(v_rows.reindex(idx, fill_value=0).mean(), 1),
            "official: oblasts with an alert start/day": round(o_r.mean(), 1),
            "volunteer: regions with an alert start/day": round(v_r.mean(), 1),
            "daily correlation of those two counts": round(float(o_r.corr(v_r)), 2),
        }
    rep.add("official vs volunteer, daily, Kyiv date of start (official with repeated copies removed):")
    rep.table(pd.DataFrame(out))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 1: data verification report")
    parser.add_argument("--latest", action="store_true",
                        help="use the newest dataset commit instead of the pinned one")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    commit, commit_time = resolve_commit(args.latest)
    official = download(config.OFFICIAL_FILE, commit)
    volunteer = download(config.VOLUNTEER_FILE, commit)
    snap = write_snapshot(commit, commit_time, {"official": official, "volunteer": volunteer})

    rep = Report()
    rep.add("# Step 1: data check")
    rep.add(f"dataset {config.DATASET_REPO} @ {commit} (committed {commit_time})")
    rep.add(f"file {config.OFFICIAL_FILE}: {snap['files']['official']['bytes']} bytes, "
            f"sha256 {snap['files']['official']['sha256']}")
    rep.add(f"file {config.VOLUNTEER_FILE}: {snap['files']['volunteer']['bytes']} bytes, "
            f"sha256 {snap['files']['volunteer']['sha256']}")

    raw = load_raw(official)
    raw_view(rep, raw)
    missing = [c for c in REQUIRED if c not in raw.columns]
    if missing:
        rep.add(f"\nSTOP: expected columns {missing} are missing; actual columns: {list(raw.columns)}")
        rep.save(config.REPORTS_DIR / "data_check.md")
        sys.exit(1)

    df = parse_times(raw)
    dup, dup_per_month = describe_duplicates(rep, raw, df)
    d = df.loc[~dup]
    coverage(rep, raw, df, d)
    values(rep, d)
    collapse_test(rep, d, dup_per_month)
    tail_check(rep, d, commit_time)
    volunteer_check(rep, volunteer, d)
    rep.save(config.REPORTS_DIR / "data_check.md")
    print(f"\nreport saved to {config.REPORTS_DIR / 'data_check.md'}")


if __name__ == "__main__":
    main()
