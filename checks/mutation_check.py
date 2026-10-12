"""Do the two unit tests really catch leakage?

Injects wrong or leaky code into a temporary COPY of src/ and tests/, one change at a time, and runs
`python -m unittest discover -s tests` on the copy. Every change should make the tests fail.

    python checks/mutation_check.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (what is broken, file, exact text to replace, replacement)
MUTANTS = [
    ("moving average without the one-day shift (includes the forecast day)", "src/models.py",
     'out[f"ma_{k}"] = prev.rolling(k).mean()', 'out[f"ma_{k}"] = y.rolling(k).mean()'),
    ("naive uses today (shift 0) instead of yesterday", "src/models.py",
     '"naive": prev,', '"naive": y,'),
    ("seasonal naive off by one day (shift 6)", "src/models.py",
     '"seasonal_naive_7": y.shift(7),', '"seasonal_naive_7": y.shift(6),'),
    ("seasonal mean uses shift 27 instead of 28", "src/models.py",
     "y.shift(21) + y.shift(28)) / 4,", "y.shift(21) + y.shift(27)) / 4,"),
    ("Ridge trains on rows up to and including the forecast day", "src/models.py",
     "rows = X.loc[(X.index >= train_start) & (X.index < day)].dropna()\n        model = _fit(rows, y.loc[rows.index], alpha)",
     "rows = X.loc[(X.index >= train_start) & (X.index <= day)].dropna()\n        model = _fit(rows, y.loc[rows.index], alpha)"),
    ("scaler fitted on all rows, including the future", "src/models.py",
     "model = _fit(rows, y.loc[rows.index], alpha)\n        out[day] = float(model.predict(X.loc[[day]])[0])",
     "scaler = StandardScaler().fit(X.dropna())\n"
     "        model = Ridge(alpha=alpha).fit(scaler.transform(rows), y.loc[rows.index])\n"
     "        out[day] = float(model.predict(scaler.transform(X.loc[[day]]))[0])"),
    ("Ridge lag_1 replaced by today (shift 0)", "src/models.py",
     'cols = {f"lag_{k}": y.shift(k) for k in RIDGE_LAGS}',
     'cols = {f"lag_{k}": y.shift(0 if k == 1 else k) for k in RIDGE_LAGS}'),
    ("Ridge gets tomorrow as an extra feature (shift -1)", "src/models.py",
     'cols["mean_28"] = prev.rolling(28).mean()',
     'cols["mean_28"] = prev.rolling(28).mean()\n    cols["future_1"] = y.shift(-1)'),
    ("alerts assigned to the UTC date instead of the Kyiv date", "src/target.py",
     "return ts.dt.tz_convert(config.TZ).dt.tz_localize(None).dt.normalize()",
     "return ts.dt.tz_localize(None).dt.normalize()"),
    ("the partial last day is kept (last complete day = day of the last record)", "src/target.py",
     "return pd.Timestamp(last.date()) - pd.Timedelta(days=1)",
     "return pd.Timestamp(last.date())"),
]


def run_tests(cwd: Path) -> tuple[bool, str]:
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=cwd,
                       capture_output=True, text=True, timeout=600)
    tail = (p.stderr or p.stdout).strip().splitlines()
    return p.returncode == 0, " | ".join(tail[-3:])[:200]


def fresh_copy(base: Path, name: str) -> Path:
    dest = base / name
    dest.mkdir(parents=True)
    for part in ("src", "tests"):
        shutil.copytree(ROOT / part, dest / part, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        ok, tail = run_tests(fresh_copy(base, "unmutated"))
        print(f"unchanged copy: tests {'pass' if ok else 'FAIL'} ({tail})")
        if not ok:
            sys.exit("the tests must pass on the unchanged code before this check means anything")
        caught = 0
        for i, (name, rel, old, new) in enumerate(MUTANTS, 1):
            dest = fresh_copy(base, f"mutant_{i}")
            path = dest / rel
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                print(f"{i:2d}. SKIPPED  {name}: pattern found {text.count(old)} times in {rel}")
                continue
            path.write_text(text.replace(old, new), encoding="utf-8")
            passed, tail = run_tests(dest)
            caught += not passed
            print(f"{i:2d}. {'CAUGHT ' if not passed else 'MISSED '} {name}")
        print(f"\n{caught} of {len(MUTANTS)} wrong versions are caught by the two tests")


if __name__ == "__main__":
    main()
