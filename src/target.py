"""Step 2: the forecasting target.

y[D] = number of volunteer alert starts in Ukraine on Kyiv calendar day D (24 regions).

Only start timestamps define the target, never end times. A forecast made at 00:00 of day D may
therefore use every start before D and nothing else. Days are Europe/Kyiv wall-clock dates, so an
alert that starts at 21:30 UTC on 11 Oct (summer time) belongs to 12 Oct.

    python -m src.target            # pinned dataset commit
    python -m src.target --latest   # newest commit of the dataset repo
"""
from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import pandas as pd

from . import config
from .data import download, load_raw, resolve_commit

REQUIRED_COLUMNS = ["region", "started_at", "finished_at", "naive"]


def load_events(path: Path) -> pd.DataFrame:
    """Read the volunteer CSV. Stops with the real column names if the layout is not as expected."""
    raw = load_raw(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"{path}: columns {missing} are missing; the file has {list(raw.columns)}")
    if raw["region"].isna().any() or raw["started_at"].isna().any():
        raise ValueError(f"{path}: empty region or started_at values; fix the data, do not guess")
    return pd.DataFrame({
        "region": raw["region"],
        "started_at": pd.to_datetime(raw["started_at"], utc=True, format="ISO8601"),  # raises on bad text
        "finished_at": pd.to_datetime(raw["finished_at"], utc=True, format="ISO8601", errors="coerce"),
        "naive": raw["naive"].str.lower().eq("true"),
    })


def clean_events(ev: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Drop excluded regions and repeated (region, started_at) rows; return the rows and what was dropped."""
    stats = {"rows_read": len(ev)}
    keep = ~ev["region"].isin(config.EXCLUDED_REGIONS)
    stats["excluded_region_rows"] = int((~keep).sum())
    ev = ev.loc[keep]
    dup = ev.duplicated(subset=["region", "started_at"])
    stats["duplicate_rows_dropped"] = int(dup.sum())
    ev = ev.loc[~dup].reset_index(drop=True)
    stats["rows_used"] = len(ev)
    return ev, stats


def kyiv_day(ts: pd.Series) -> pd.Series:
    """UTC timestamps -> Kyiv calendar day (midnight, no tz info)."""
    return ts.dt.tz_convert(config.TZ).dt.tz_localize(None).dt.normalize()


def last_complete_day(ev: pd.DataFrame) -> pd.Timestamp:
    """The Kyiv day of the last record is still running when the file is written, so it is dropped."""
    last = ev["started_at"].max().tz_convert(config.TZ)
    return pd.Timestamp(last.date()) - pd.Timedelta(days=1)


def daily_starts(ev: pd.DataFrame, last_day: pd.Timestamp | None = None) -> pd.Series:
    """Alert starts per Kyiv day up to and including `last_day`; days without a start are 0."""
    last_day = last_complete_day(ev) if last_day is None else pd.Timestamp(last_day)
    day = kyiv_day(ev["started_at"])
    counts = day[day <= last_day].value_counts().sort_index()
    y = counts.reindex(pd.date_range(counts.index.min(), last_day, freq="D"), fill_value=0)
    y.index.name = "day"
    return y.astype("float64").rename("alert_starts")


def zero_days(y: pd.Series) -> list[pd.Timestamp]:
    """Days with no alert start anywhere in the country: implausible, so they are listed, not hidden."""
    return list(y.index[y == 0])


def build_target(path: Path) -> tuple[pd.Series, pd.DataFrame, dict]:
    ev, stats = clean_events(load_events(path))
    stats["last_record_kyiv"] = ev["started_at"].max().tz_convert(config.TZ).strftime("%Y-%m-%d %H:%M")
    y = daily_starts(ev)
    zd = zero_days(y)
    stats["zero_days"] = [f"{d:%Y-%m-%d}" for d in zd]
    if zd:
        warnings.warn(f"{len(zd)} day(s) with zero alert starts nationwide (outage?): "
                      + ", ".join(f"{d:%Y-%m-%d}" for d in zd))
    return y, ev, stats


def describe(y: pd.Series, stats: dict, commit: str) -> str:
    wk = y.groupby(y.index.dayofweek).mean().round(1)
    wk.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    monthly = y.groupby(y.index.to_period("M")).mean().round(1).tail(24)
    lines = [
        "# Target: alert starts per Kyiv day (volunteer file)",
        "",
        f"- source: {config.VOLUNTEER_FILE} @ {commit}",
        f"- rows read {stats['rows_read']}; excluded regions {list(config.EXCLUDED_REGIONS)}: "
        f"{stats['excluded_region_rows']} rows; repeated (region, started_at): "
        f"{stats['duplicate_rows_dropped']} rows; rows used {stats['rows_used']}",
        f"- last record {stats['last_record_kyiv']} Kyiv, so the last complete day is {y.index.max():%Y-%m-%d}; "
        "the day of the last record is partial and dropped",
        f"- series {y.index.min():%Y-%m-%d} .. {y.index.max():%Y-%m-%d}: {len(y)} days",
        f"- days with zero starts nationwide: {len(stats['zero_days'])}"
        + (f" ({', '.join(stats['zero_days'])}); kept as they are, not filled or dropped" if stats["zero_days"] else ""),
        f"- all days: mean {y.mean():.1f}, std {y.std():.1f}, min {y.min():.0f}, max {y.max():.0f}",
        "",
        "Mean starts by weekday, all days:",
        "```",
        wk.to_string(),
        "```",
        "Mean starts per day by month, last 24 months:",
        "```",
        monthly.to_string(),
        "```",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(y: pd.Series, stats: dict, commit: str) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    y.to_csv(config.PROCESSED_DIR / "daily.csv", encoding="utf-8")
    (config.REPORTS_DIR / "target_check.md").write_text(describe(y, stats, commit), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 2: build the daily target")
    parser.add_argument("--latest", action="store_true", help="use the newest dataset commit")
    args = parser.parse_args(argv)
    commit, _ = resolve_commit(args.latest)
    y, _, stats = build_target(download(config.VOLUNTEER_FILE, commit))
    write_outputs(y, stats, commit)
    print((config.REPORTS_DIR / "target_check.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
