"""Step 3: chronological split. train < validation < test, test = the latest period.

Validation is used to choose settings (moving-average window, and later the training window of a
model). Test is only scored, never used to choose anything.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import config


@dataclass(frozen=True)
class Split:
    train: pd.DatetimeIndex
    val: pd.DatetimeIndex
    test: pd.DatetimeIndex

    def describe(self) -> str:
        def span(i: pd.DatetimeIndex) -> str:
            return f"{i[0]:%Y-%m-%d} ({i[0]:%a}) .. {i[-1]:%Y-%m-%d} ({i[-1]:%a}), {len(i)} days"
        return f"train {span(self.train)}; validation {span(self.val)}; test {span(self.test)}"


def make_split(index: pd.DatetimeIndex, test_days: int = config.TEST_DAYS, val_days: int = config.VAL_DAYS,
               min_train_days: int = 365) -> Split:
    """Last `test_days` days = test, the `val_days` before them = validation, the rest = train."""
    one_day = pd.Timedelta(days=1)
    if not index.is_monotonic_increasing or not (index[1:] - index[:-1] == one_day).all():
        raise ValueError("the series must have exactly one row per calendar day, in order")
    if len(index) < min_train_days + val_days + test_days:
        raise ValueError(f"{len(index)} days is too short for {min_train_days} train + {val_days} + {test_days}")
    train, val, test = index[:-(val_days + test_days)], index[-(val_days + test_days):-test_days], index[-test_days:]
    if not (train[-1] < val[0] and val[-1] < test[0]):
        raise ValueError("split is not chronological")
    if val[0] - train[-1] != one_day or test[0] - val[-1] != one_day:
        raise ValueError("split parts are not adjacent")
    return Split(train, val, test)
