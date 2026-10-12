# Results: one-day-ahead forecasts of daily alert starts

- dataset commit d10c80fa696bab42822b9f05b423fc8a30e79d20; train 2022-02-25 (Fri) .. 2026-06-21 (Sun), 1578 days; validation 2026-06-22 (Mon) .. 2026-08-16 (Sun), 56 days; test 2026-08-17 (Mon) .. 2026-10-11 (Sun), 56 days
- mean starts per day: validation 111.6, test 148.1 (the level drifts upward over time)
- chosen on validation only: moving average window ma_28; Ridge alpha 0.1 with training window 'all_history' (from 2022-02-25); best model overall ma_28 (marked *). Test numbers were not used for any choice.
- skill = 1 - MAE / MAE of naive ('same as yesterday'); above 0 means better than naive; bias = mean(forecast - actual)

```
                  val_MAE  val_skill  val_bias  test_MAE  test_RMSE  test_MAE_%_of_mean  test_skill  test_bias
naive              20.089      0.000     1.482    16.964     21.552              11.451       0.000     -1.393
seasonal_naive_7   21.696     -0.080    -1.054    27.679     33.595              18.684      -0.632     -6.464
seasonal_mean_4w   15.580      0.224    -1.188    21.879     28.764              14.769      -0.290    -14.237
ma_3               15.244      0.241     1.792    16.280     20.367              10.989       0.040     -3.113
ma_7               14.923      0.257     0.934    18.679     23.448              12.608      -0.101     -4.663
ma_14              13.555      0.325    -0.435    21.851     26.593              14.750      -0.288     -6.749
ma_28 *            12.434      0.381    -0.927    20.536     25.933              13.863      -0.211    -12.031
ridge              13.234      0.341    -1.895    18.592     22.837              12.550      -0.096     -9.285
```

Ridge settings tried (validation MAE, walk-forward, refitted at every origin):
```
 alpha train_window  val_MAE
   0.1  all_history   13.234
   0.1 after_switch   13.731
   1.0  all_history   13.239
   1.0 after_switch   13.730
  10.0  all_history   13.287
  10.0 after_switch   13.708
 100.0  all_history   13.594
 100.0 after_switch   13.562
```
