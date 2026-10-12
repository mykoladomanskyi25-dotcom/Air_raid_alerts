# Target: alert starts per Kyiv day (volunteer file)

- source: datasets/volunteer_data_en.csv @ d10c80fa696bab42822b9f05b423fc8a30e79d20
- rows read 116174; excluded regions ['Luhanska oblast']: 3 rows; repeated (region, started_at): 0 rows; rows used 116171
- last record 2026-10-12 07:49 Kyiv, so the last complete day is 2026-10-11; the day of the last record is partial and dropped
- series 2022-02-25 .. 2026-10-11: 1690 days
- days with zero starts nationwide: 0
- all days: mean 68.7, std 31.4, min 6, max 198

Mean starts by weekday, all days:
```
Mon    68.4
Tue    69.6
Wed    70.2
Thu    71.5
Fri    71.1
Sat    67.2
Sun    63.1
```
Mean starts per day by month, last 24 months:
```
day
2024-11     62.9
2024-12     57.2
2025-01     62.9
2025-02     62.0
2025-03     55.3
2025-04     60.2
2025-05     57.1
2025-06     61.2
2025-07     72.4
2025-08     69.5
2025-09     72.3
2025-10     73.9
2025-11     83.5
2025-12     79.5
2026-01     89.8
2026-02     91.4
2026-03    107.8
2026-04    100.0
2026-05    109.7
2026-06    109.9
2026-07    109.9
2026-08    126.0
2026-09    148.3
2026-10    158.0
Freq: M
```
