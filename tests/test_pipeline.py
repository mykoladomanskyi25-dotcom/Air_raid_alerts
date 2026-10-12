"""Two tests, on synthetic data only (no download):

1. an alert that crosses midnight is counted once, on the Kyiv day it starts;
2. the truncation test: the forecast for day D is the same when every record from 00:00 of D onward is cut off.

    python -m unittest discover -s tests
"""
import unittest

import numpy as np
import pandas as pd

from src import config
from src.models import BASELINES, forecast_all, predict_next, ridge_predict_next, ridge_walk_forward
from src.target import daily_starts, last_complete_day


def events(rows):
    """rows: (started_at, finished_at) as UTC text."""
    return pd.DataFrame({
        "region": "Kyivska oblast",
        "started_at": pd.to_datetime([r[0] for r in rows], utc=True),
        "finished_at": pd.to_datetime([r[1] for r in rows], utc=True),
    })


def synthetic_events(days: int = 150, seed: int = 7) -> pd.DataFrame:
    """A made-up alert history: weekly rhythm and an upward drift, start times spread over each UTC day."""
    rng = np.random.RandomState(seed)
    t0 = pd.Timestamp("2026-04-01", tz="UTC")
    times = []
    for i in range(days):
        n = rng.poisson(60 + 12 * np.sin(2 * np.pi * i / 7) + 0.4 * i)
        times += list(t0 + pd.Timedelta(days=i) + pd.to_timedelta(rng.randint(0, 86400, size=n), unit="s"))
    ev = pd.DataFrame({"region": "Kyivska oblast", "started_at": pd.DatetimeIndex(times)})
    return ev.sort_values("started_at").reset_index(drop=True)


class TestTarget(unittest.TestCase):
    def test_alert_crossing_midnight_is_counted_on_the_day_it_starts(self):
        # summer time, UTC+3 (DST ends on 25 Oct 2026)
        summer = events([
            ("2026-10-11 20:50:00", "2026-10-11 21:20:00"),  # 23:50 Kyiv on 11 Oct, ends 00:20 on 12 Oct
            ("2026-10-11 21:30:00", "2026-10-11 22:00:00"),  # 00:30 Kyiv on 12 Oct (UTC date is still 11 Oct)
            ("2026-10-12 04:49:00", "2026-10-12 05:10:00"),  # last record, 07:49 Kyiv on 12 Oct
        ])
        self.assertEqual(last_complete_day(summer), pd.Timestamp("2026-10-11"))
        y = daily_starts(summer)  # the day of the last record is partial and dropped
        self.assertEqual(list(y.index), [pd.Timestamp("2026-10-11")])
        self.assertEqual(y.iloc[0], 1.0)  # only the alert that started at 23:50; its end time plays no role
        y = daily_starts(summer, last_day=pd.Timestamp("2026-10-12"))
        self.assertEqual(y.to_dict(), {pd.Timestamp("2026-10-11"): 1.0, pd.Timestamp("2026-10-12"): 2.0})
        # winter time, UTC+2: the same UTC clock time falls on the other side of midnight
        winter = events([
            ("2026-11-01 21:30:00", "2026-11-01 22:10:00"),  # 23:30 Kyiv on 1 Nov
            ("2026-11-01 22:30:00", "2026-11-01 23:00:00"),  # 00:30 Kyiv on 2 Nov
        ])
        y = daily_starts(winter, last_day=pd.Timestamp("2026-11-02"))
        self.assertEqual(y.to_dict(), {pd.Timestamp("2026-11-01"): 1.0, pd.Timestamp("2026-11-02"): 1.0})


class TestTruncation(unittest.TestCase):
    def test_forecast_for_day_d_is_unchanged_when_everything_from_d_is_cut(self):
        ev = synthetic_events()
        y = daily_starts(ev, last_complete_day(ev))
        full = forecast_all(y)  # the fast pipeline, run once on all data
        leaky = y.rolling(7).mean()  # a 7-day mean that forgot shift(1): it includes day D itself
        leak_caught = False
        for origin in y.index[70::7]:  # 00:00 Kyiv of day D is the moment the forecast is made
            cut_at = origin.tz_localize(config.TZ).tz_convert("UTC")
            cut = ev.loc[ev["started_at"] < cut_at]  # physically remove every record from D onward
            y_cut = daily_starts(cut, last_day=origin - pd.Timedelta(days=1))
            self.assertEqual(y_cut.index[-1], origin - pd.Timedelta(days=1))
            for model in BASELINES:
                self.assertAlmostEqual(predict_next(y_cut, model), full.loc[origin, model], places=9,
                                       msg=f"{model} for {origin:%Y-%m-%d} depends on data from that day or later")
            bumped = y.copy()
            bumped.loc[origin:] += 1000  # whatever happens on D or later must not move the forecast for D
            pd.testing.assert_series_equal(forecast_all(bumped).loc[origin], full.loc[origin])
            leak_caught |= abs(leaky.loc[origin] - predict_next(y_cut, "ma_7")) > 1e-6
            # the Ridge: fast walk-forward on all data vs rebuilt from the cut history, and insensitive to the future
            for alpha, start in ((10.0, y.index.min()), (1.0, y.index[60])):
                fast = ridge_walk_forward(y, [origin], alpha, start)[origin]
                self.assertAlmostEqual(ridge_predict_next(y_cut, alpha, start), fast, places=6,
                                       msg=f"ridge for {origin:%Y-%m-%d} depends on data from that day or later")
                self.assertAlmostEqual(ridge_walk_forward(bumped, [origin], alpha, start)[origin], fast, places=6)
        self.assertTrue(leak_caught, "the check is too weak: a moving average without shift(1) passed it")


if __name__ == "__main__":
    unittest.main()
