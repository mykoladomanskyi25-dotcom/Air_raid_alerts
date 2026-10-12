"""Two questions on the real data, with the settings the pipeline chose.

1. Does anything chosen on validation depend on the test window? The test window is overwritten (x3 plus noise)
   and everything that is chosen on validation, and every validation score, must stay the same.
2. Does a forecast for day D depend on day D or later? Day D and everything after it is changed by +1000 and the
   forecast for D must stay the same, for the baselines and for Ridge.

Needs the data/ folder from `python -m src.pipeline`.

    python checks/isolation_check.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import config  # noqa: E402
from src.check_measurement import find_switch_day, official_daily_by_level  # noqa: E402
from src.evaluate import choose_ridge, score, select_on_validation  # noqa: E402
from src.models import forecast_all, ridge_walk_forward  # noqa: E402
from src.split import make_split  # noqa: E402


def main() -> None:
    y = pd.read_csv(config.PROCESSED_DIR / "daily.csv", index_col="day", parse_dates=True)["alert_starts"]
    split = make_split(y.index)
    official = config.RAW_DIR / config.DATASET_COMMIT / "official_data_en.csv"
    switch_day = find_switch_day(official_daily_by_level(official))

    def everything(yy):
        fc = forecast_all(yy)
        grid, cfg = choose_ridge(yy, split, switch_day)
        fc["ridge"] = ridge_walk_forward(yy, split.val.union(split.test), cfg["alpha"], cfg["train_start"])
        sc = score(yy, fc, split)
        return fc, grid, cfg, sc, select_on_validation(sc)

    fc0, grid0, cfg0, sc0, ch0 = everything(y)
    rng = np.random.RandomState(1)
    y_changed = y.copy()
    y_changed.loc[split.test] = y_changed.loc[split.test] * 3 + rng.randint(0, 500, len(split.test))
    fc1, grid1, cfg1, sc1, ch1 = everything(y_changed)

    def numbers(df):
        return df.select_dtypes("number")

    val0, val1 = sc0[sc0["split"] == "validation"], sc1[sc1["split"] == "validation"]
    test0, test1 = sc0[sc0["split"] == "test"], sc1[sc1["split"] == "test"]
    print("1) test window overwritten:")
    print("   validation scores unchanged       :", bool(np.allclose(numbers(val0), numbers(val1), equal_nan=True)))
    print("   Ridge grid on validation unchanged:", bool(np.allclose(grid0["val_MAE"], grid1["val_MAE"])))
    print("   choices unchanged                 :", ch0 == ch1 and cfg0 == cfg1, ch0, cfg0["alpha"], cfg0["train_window"])
    print("   first test day forecast unchanged :", bool(np.allclose(fc0.loc[split.test[0]], fc1.loc[split.test[0]])))
    print("   test scores changed (expected)    :", not bool(np.allclose(numbers(test0), numbers(test1))))

    print("2) day D and everything after it changed by +1000:")
    for day in [split.val[0], split.val[30], split.test[0], split.test[28], split.test[-1]]:
        y_future = y.copy()
        y_future.loc[day:] += 1000
        baselines_same = bool(np.allclose(forecast_all(y).loc[day], forecast_all(y_future).loc[day]))
        r0 = ridge_walk_forward(y, [day], cfg0["alpha"], cfg0["train_start"])[day]
        r1 = ridge_walk_forward(y_future, [day], cfg0["alpha"], cfg0["train_start"])[day]
        print(f"   {day:%Y-%m-%d}: baselines unchanged {baselines_same}; Ridge difference {abs(r0 - r1):.1e}")


if __name__ == "__main__":
    main()
