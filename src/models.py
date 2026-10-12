"""Step 4: baselines and a Ridge model. Every forecast for day D uses only days before D.

Fast versions (used for the reported numbers)
  forecast_all        baselines, vectorised: every input is shifted before it is used, so row D never sees y[D].
  ridge_walk_forward  Ridge, refitted at every forecast origin on the days before that origin.
Reference versions (used by the truncation test)
  predict_next, ridge_predict_next
                      forecast for the day after the last day of the history they are given, rebuilt from that
                      history alone. If a fast version used anything from day D or later, it would disagree.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MA_WINDOWS = (3, 7, 14, 28)
BASELINES = ("naive", "seasonal_naive_7", "seasonal_mean_4w") + tuple(f"ma_{k}" for k in MA_WINDOWS)
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
RIDGE_LAGS = (1, 2, 3, 4, 5, 6, 7, 14)


def forecast_all(y: pd.Series) -> pd.DataFrame:
    """One-step-ahead forecast of every baseline for every day. NaN until enough history exists."""
    prev = y.shift(1)  # the only way a moving average sees y: through yesterday
    out = {
        "naive": prev,                                                                  # same as yesterday
        "seasonal_naive_7": y.shift(7),                                                 # same weekday last week
        "seasonal_mean_4w": (y.shift(7) + y.shift(14) + y.shift(21) + y.shift(28)) / 4,  # same weekday, 4 weeks
    }
    for k in MA_WINDOWS:
        out[f"ma_{k}"] = prev.rolling(k).mean()                                         # mean of the last k days
    return pd.DataFrame(out)[list(BASELINES)]


def predict_next(history: pd.Series, model: str) -> float:
    """Baseline forecast for the day after `history` ends, from `history` alone."""
    h = history.to_numpy(dtype="float64")
    if model == "naive":
        return float(h[-1])
    if model == "seasonal_naive_7":
        return float(h[-7])
    if model == "seasonal_mean_4w":
        return float((h[-7] + h[-14] + h[-21] + h[-28]) / 4)
    if model.startswith("ma_"):
        return float(np.mean(h[-int(model[3:]):]))
    raise ValueError(f"unknown model {model!r}")


def make_features(y: pd.Series) -> pd.DataFrame:
    """Row D: y of earlier days (lags, shifted rolling means) and the weekday of D, a calendar fact known in advance."""
    prev = y.shift(1)
    cols = {f"lag_{k}": y.shift(k) for k in RIDGE_LAGS}
    cols["mean_7"] = prev.rolling(7).mean()
    cols["mean_28"] = prev.rolling(28).mean()
    X = pd.DataFrame(cols)
    for d in range(1, 7):  # Monday is the reference weekday
        X[f"dow_{d}"] = (y.index.dayofweek == d).astype("float64")
    return X


def _fit(rows: pd.DataFrame, target: pd.Series, alpha: float):
    # the scaler lives inside the pipeline, so it is fitted on the training rows only
    return make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(rows, target)


def ridge_walk_forward(y: pd.Series, origins, alpha: float, train_start: pd.Timestamp) -> pd.Series:
    """Forecast each origin day with a Ridge refitted on the days from `train_start` up to the day before it."""
    X = make_features(y)  # row t only contains y before t, so building it once is safe
    out = {}
    for day in origins:
        rows = X.loc[(X.index >= train_start) & (X.index < day)].dropna()
        model = _fit(rows, y.loc[rows.index], alpha)
        out[day] = float(model.predict(X.loc[[day]])[0])
    return pd.Series(out, name="ridge")


def ridge_predict_next(history: pd.Series, alpha: float, train_start: pd.Timestamp) -> float:
    """Reference: the same forecast built from `history` alone, with the forecast day appended as unknown."""
    day = history.index[-1] + pd.Timedelta(days=1)
    ext = pd.concat([history, pd.Series([np.nan], index=pd.DatetimeIndex([day]))])
    X = make_features(ext)
    rows = X.loc[(X.index >= train_start) & (X.index < day)].dropna()
    model = _fit(rows, history.loc[rows.index], alpha)
    return float(model.predict(X.loc[[day]])[0])
