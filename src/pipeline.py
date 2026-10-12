"""One command for the whole pipeline.

    python -m src.pipeline            # dataset pinned in src/config.py
    python -m src.pipeline --latest   # newest dataset commit instead

download -> data report (Step 1) -> target -> measurement check -> split -> baselines -> evaluation.
Everything it writes is in data/ (not tracked) and reports/ (tracked).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys

from . import check_measurement, config, evaluate, inspect_data, target
from .data import download, resolve_commit
from .split import make_split


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the whole pipeline")
    parser.add_argument("--latest", action="store_true", help="use the newest dataset commit")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    commit, commit_time = resolve_commit(args.latest)
    print(f"dataset {config.DATASET_REPO} @ {commit} (committed {commit_time})")
    official = download(config.OFFICIAL_FILE, commit)
    volunteer = download(config.VOLUNTEER_FILE, commit)

    print("1/4 data report -> reports/data_check.md")
    with contextlib.redirect_stdout(io.StringIO()):  # the report is long; it is saved to the file
        inspect_data.run(commit, commit_time)

    print("2/4 target -> data/processed/daily.csv, reports/target_check.md")
    y, _, stats = target.build_target(volunteer)
    target.write_outputs(y, stats, commit)
    print(f"    {len(y)} days, {y.index.min():%Y-%m-%d} .. {y.index.max():%Y-%m-%d}; "
          f"zero-start days: {len(stats['zero_days'])}")

    print("3/4 measurement check -> reports/volunteer_measurement_check.md")
    with contextlib.redirect_stdout(io.StringIO()):
        meas = check_measurement.run(volunteer, official, commit)
    t = meas["test"]
    print(f"    switch day {meas['switch_day']:%Y-%m-%d}; ratio {t['ratio']:.3f}, rank {t['rank']} of {t['of']} "
          f"-> {'JUMP' if t['jump'] else 'no jump'} at the switch")

    print("4/4 split, baselines, evaluation -> reports/results.md")
    split = make_split(y.index)
    evaluate.run(y, split, meas["switch_day"], commit)
    print()
    print((config.REPORTS_DIR / "results.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
