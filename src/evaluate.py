"""Step 5: walk-forward evaluation of the baselines and Ridge, and the choices made on validation.

One-step-ahead, walk-forward: for every day in the evaluation window we act as if it were 00:00 of that day,
use only earlier days, and record the forecast for that day; then we move on by one day. Settings (moving-average
window, Ridge alpha and training window) are chosen on validation; the test window is only scored.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, plotting
from .models import BASELINES, RIDGE_ALPHAS, forecast_all, predict_next, ridge_predict_next, ridge_walk_forward
from .split import Split


def metrics(actual: pd.Series, pred: pd.Series) -> dict:
    if pred.isna().any():
        raise ValueError("forecast has gaps inside the evaluation window")
    err = pred - actual
    mae = float(err.abs().mean())
    return {"days": len(actual), "mean_actual": float(actual.mean()), "MAE": mae,
            "RMSE": float(np.sqrt((err ** 2).mean())), "MAE_pct_of_mean": 100 * mae / float(actual.mean()),
            "bias": float(err.mean())}  # forecast minus actual; negative = the forecast runs low


def score(y: pd.Series, forecasts: pd.DataFrame, split: Split) -> pd.DataFrame:
    rows = []
    for part, idx in (("validation", split.val), ("test", split.test)):
        for model in forecasts.columns:
            rows.append({"split": part, "model": model, **metrics(y.loc[idx], forecasts.loc[idx, model])})
    df = pd.DataFrame(rows)
    naive_mae = df.loc[df["model"] == "naive"].set_index("split")["MAE"]
    df["skill_vs_naive"] = 1 - df["MAE"] / df["split"].map(naive_mae)  # > 0: better than "same as yesterday"
    return df


def choose_ridge(y: pd.Series, split: Split, switch_day: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Alpha and training window (all history vs after the switch) by validation MAE. Test is not touched."""
    windows = {"all_history": y.index.min(), "after_switch": switch_day}
    rows = []
    for alpha in RIDGE_ALPHAS:
        for name, start in windows.items():
            pred = ridge_walk_forward(y, split.val, alpha, start)
            rows.append({"alpha": alpha, "train_window": name, "train_start": start,
                         "val_MAE": metrics(y.loc[split.val], pred)["MAE"]})
    grid = pd.DataFrame(rows)
    best = grid.loc[grid["val_MAE"].idxmin()]
    return grid, {"alpha": float(best["alpha"]), "train_window": best["train_window"],
                  "train_start": best["train_start"]}


def select_on_validation(scores: pd.DataFrame) -> dict:
    """The only place where a model or setting is chosen: validation MAE."""
    val = scores.loc[scores["split"] == "validation"].set_index("model")["MAE"]
    return {"best_ma": val[val.index.str.startswith("ma_")].idxmin(), "best_overall": val.idxmin()}


def plot_series(y: pd.Series, split: Split, switch_day: pd.Timestamp, path) -> None:
    fig, (ax,) = plotting.new_figure(1, height_per_row=3.6)
    ax.plot(y.index, y, color=plotting.BLUE, lw=0.6, alpha=0.45, label="alert starts per day")
    ax.plot(y.index, y.rolling(7).mean(), color=plotting.BLUE, lw=1.4, label="7-day mean")
    one = pd.Timedelta(days=1)
    for idx, name, ha, x in ((split.val, "validation ", "right", split.val[0]),
                             (split.test, " test", "left", split.test[-1] + one)):
        ax.axvspan(idx[0], idx[-1] + one, color=plotting.GRID, alpha=0.6, lw=0)
        ax.text(x, 1.01, name, transform=ax.get_xaxis_transform(), fontsize=8, color=plotting.INK_2, ha=ha)
    ax.axvline(switch_day, color=plotting.INK_2, lw=0.8, ls=(0, (4, 3)))
    ax.text(switch_day, 1.01, f"official switch {switch_day:%Y-%m-%d} ", transform=ax.get_xaxis_transform(),
            fontsize=8, color=plotting.INK_2, ha="right")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    plotting.save(fig, path, "Daily alert starts (volunteer file, 24 regions) and the chronological split")


def plot_test(y: pd.Series, forecasts: pd.DataFrame, split: Split, chosen: dict, path) -> None:
    fig, (ax,) = plotting.new_figure(1, height_per_row=3.8)
    ax.plot(split.test, y.loc[split.test], color=plotting.INK, lw=1.6, label="actual")
    names = list(dict.fromkeys(["naive", chosen["best_ma"], chosen["best_overall"]]))
    for name, color in zip(names, (plotting.AQUA, plotting.ORANGE, plotting.BLUE)):
        tag = " (best on validation)" if name == chosen["best_overall"] else ""
        ax.plot(split.test, forecasts.loc[split.test, name], color=color, lw=1.1, label=name + tag)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    plotting.save(fig, path, f"Test window {split.test[0]:%Y-%m-%d} .. {split.test[-1]:%Y-%m-%d}: "
                             "one-day-ahead forecasts vs actual")


def write_next_day(y: pd.Series, ridge_cfg: dict, chosen: dict, commit: str) -> pd.DataFrame:
    """Forecast for the day after the last complete day, made at 00:00 of that day. Score it once that day is complete."""
    day = y.index[-1] + pd.Timedelta(days=1)
    rows = [{"model": m, "forecast": predict_next(y, m)} for m in BASELINES]
    rows.append({"model": "ridge", "forecast": ridge_predict_next(y, ridge_cfg["alpha"], ridge_cfg["train_start"])})
    df = pd.DataFrame(rows)
    df.insert(0, "forecast_day", f"{day:%Y-%m-%d}")
    df["forecast"] = df["forecast"].round(2)
    df["chosen_on_validation"] = df["model"].isin([chosen["best_overall"], chosen["best_ma"], "ridge"])
    df["data_through"] = f"{y.index[-1]:%Y-%m-%d}"
    df["dataset_commit"] = commit
    df.to_csv(config.REPORTS_DIR / f"next_day_forecast_{day:%Y-%m-%d}.csv", index=False, encoding="utf-8")
    return df


def run(y: pd.Series, split: Split, switch_day: pd.Timestamp, commit: str) -> dict:
    forecasts = forecast_all(y)
    grid, ridge_cfg = choose_ridge(y, split, switch_day)  # validation only
    evaluated = split.val.union(split.test)
    forecasts["ridge"] = ridge_walk_forward(y, evaluated, ridge_cfg["alpha"], ridge_cfg["train_start"])
    scores = score(y, forecasts, split)
    chosen = select_on_validation(scores)  # recorded before the test numbers are read below

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(config.REPORTS_DIR / "results.csv", index=False, encoding="utf-8")
    forecasts.loc[evaluated].round(3).to_csv(config.REPORTS_DIR / "forecasts.csv", encoding="utf-8")

    wide = scores.pivot(index="model", columns="split",
                        values=["MAE", "RMSE", "MAE_pct_of_mean", "skill_vs_naive", "bias"])
    table = pd.DataFrame({
        "val_MAE": wide[("MAE", "validation")], "val_skill": wide[("skill_vs_naive", "validation")],
        "val_bias": wide[("bias", "validation")],
        "test_MAE": wide[("MAE", "test")], "test_RMSE": wide[("RMSE", "test")],
        "test_MAE_%_of_mean": wide[("MAE_pct_of_mean", "test")], "test_skill": wide[("skill_vs_naive", "test")],
        "test_bias": wide[("bias", "test")],
    }).loc[forecasts.columns].round(3)
    table.index = [f"{m} *" if m == chosen["best_overall"] else m for m in table.index]
    shown_grid = grid.drop(columns="train_start").assign(val_MAE=grid["val_MAE"].round(3))
    mean_val, mean_test = y.loc[split.val].mean(), y.loc[split.test].mean()
    text = "\n".join([
        "# Results: one-day-ahead forecasts of daily alert starts",
        "",
        f"- dataset commit {commit}; {split.describe()}",
        f"- mean starts per day: validation {mean_val:.1f}, test {mean_test:.1f} (the level drifts upward over time)",
        f"- chosen on validation only: moving average window {chosen['best_ma']}; Ridge alpha "
        f"{ridge_cfg['alpha']:g} with training window '{ridge_cfg['train_window']}' "
        f"(from {ridge_cfg['train_start']:%Y-%m-%d}); best model overall {chosen['best_overall']} (marked *). "
        "Test numbers were not used for any choice.",
        "- skill = 1 - MAE / MAE of naive ('same as yesterday'); above 0 means better than naive; "
        "bias = mean(forecast - actual)",
        "",
        "```",
        table.to_string(),
        "```",
        "",
        "Ridge settings tried (validation MAE, walk-forward, refitted at every origin):",
        "```",
        shown_grid.to_string(index=False),
        "```",
        "",
    ])
    (config.REPORTS_DIR / "results.md").write_text(text, encoding="utf-8")
    plot_series(y, split, switch_day, config.REPORTS_DIR / "fig_series_and_splits.png")
    plot_test(y, forecasts, split, chosen, config.REPORTS_DIR / "fig_test.png")
    next_day = write_next_day(y, ridge_cfg, chosen, commit)
    return {"scores": scores, "table": table, "chosen": chosen, "ridge": ridge_cfg, "forecasts": forecasts,
            "next_day": next_day}
