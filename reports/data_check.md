# Step 1: data check
dataset Vadimkin/ukrainian-air-raid-sirens-dataset @ d10c80fa696bab42822b9f05b423fc8a30e79d20 (committed 2026-10-12T05:05:17Z)
file datasets/official_data_en.csv: 31025633 bytes, sha256 b396f87696243069eec0219880e87dcd642b20beb0a7bae0d0e1f61e1ed20ec4
file datasets/volunteer_data_en.csv: 8921292 bytes, sha256 b6c0160f0b4e6a83fa0d6f5dfbf1a3c623b6122819d37185f99b57d7587da14b

## 1. Raw view (every column read as text)

shape: (299275, 7)
columns: ['oblast', 'raion', 'hromada', 'level', 'started_at', 'finished_at', 'source']
```
oblast         str
raion          str
hromada        str
level          str
started_at     str
finished_at    str
source         str
```
head(5):
```
                 oblast               raion                                            hromada    level                 started_at                finished_at    source
0      Vinnytska oblast                 NaN                                                NaN   oblast  2022-03-15 16:10:34+00:00  2022-03-15 16:50:07+00:00  official
1    Zhytomyrska oblast                 NaN                                                NaN   oblast  2022-03-15 16:11:25+00:00  2022-03-15 16:54:23+00:00  official
2      Cherkaska oblast      Umanskyi raion                       Umanska terytorialna hromada  hromada  2022-03-15 16:11:50+00:00  2022-03-15 16:54:47+00:00  official
3    Mykolaivska oblast  Pervomaiskyi raion  m. Pervomaisk ta Pervomaiska terytorialna hromada  hromada  2022-03-15 16:14:46+00:00  2022-03-15 16:57:08+00:00  official
4  Kirovohradska oblast                 NaN                                                NaN   oblast  2022-03-15 16:15:11+00:00  2022-03-15 16:54:52+00:00  official
```
tail(5):
```
                        oblast              raion hromada  level                 started_at                finished_at    source
299270  Dnipropetrovska oblast   Kamianskyi raion     NaN  raion  2026-09-07 04:32:52+00:00  2026-09-07 05:20:20+00:00  official
299271  Dnipropetrovska oblast  Kryvorizkyi raion     NaN  raion  2026-09-07 04:32:58+00:00  2026-09-07 05:37:53+00:00  official
299272        Poltavska oblast   Poltavskyi raion     NaN  raion  2026-09-07 04:38:21+00:00  2026-09-07 04:56:59+00:00  official
299273           Sumska oblast  Konotopskyi raion     NaN  raion  2026-09-07 05:12:16+00:00  2026-09-07 05:38:04+00:00  official
299274  Dnipropetrovska oblast   Kamianskyi raion     NaN  raion  2026-09-07 05:28:22+00:00  2026-09-07 05:38:32+00:00  official
```
raw started_at strings (first, middle, last row): '2022-03-15 16:10:34+00:00', '2024-01-14 11:44:05+00:00', '2026-09-07 05:28:22+00:00'
empty values per column, by level:
```
         oblast   raion  hromada  level  started_at  finished_at  source
level                                                                   
hromada       0       0        0      0           0            0       0
oblast        0  130235   130235      0           0            0       0
raion         0       0   132251      0           0            0       0
```
source value counts:
```
source
official    299275
```

## 2. Duplicates, coverage, durations

exact duplicate rows (second and later copies): 113845 of 299275 (38.0%); duplicates on ['oblast', 'raion', 'hromada', 'level', 'started_at']: 113845
repeated copies sit at file rows 113911 .. 227831 and cover started_at 2022-03-15 .. 2026-01-25
repeated copies per month (Kyiv time of start):
```
         repeated_copies_removed  share_of_month_rows
month                                                
2022-03                     1640                 0.50
2022-04                     2471                 0.50
2022-05                     2220                 0.50
2022-06                     1904                 0.50
2022-07                     1592                 0.50
2022-08                     1938                 0.50
2022-09                     1841                 0.50
2022-10                     1752                 0.50
2022-11                     1054                 0.50
2022-12                     1063                 0.50
2023-01                     1024                 0.50
2023-02                     1179                 0.50
2023-03                     1460                 0.50
2023-04                      866                 0.50
2023-05                     1419                 0.50
2023-06                     1437                 0.50
2023-07                     1495                 0.50
2023-08                     2012                 0.50
2023-09                     1523                 0.50
2023-10                     1656                 0.50
2023-11                     1518                 0.50
2023-12                     1788                 0.50
2024-01                     1937                 0.50
2024-02                     1838                 0.50
2024-03                     2773                 0.50
2024-04                     2223                 0.50
2024-05                     2736                 0.50
2024-06                     2517                 0.50
2024-07                     2284                 0.50
2024-08                     2207                 0.50
2024-09                     2115                 0.50
2024-10                     1997                 0.50
2024-11                     1803                 0.50
2024-12                     1704                 0.50
2025-01                     2020                 0.50
2025-02                     1967                 0.50
2025-03                     2004                 0.50
2025-04                     2228                 0.50
2025-05                     2268                 0.50
2025-06                     2427                 0.50
2025-07                     3060                 0.50
2025-08                     4178                 0.50
2025-09                     4737                 0.50
2025-10                     4915                 0.50
2025-11                     8053                 0.50
2025-12                     8034                 0.50
2026-01                     6968                 0.45
```
parsed dtypes: started_at datetime64[us, UTC], finished_at datetime64[us, UTC]
```
                               min_utc                    max_utc                   min_kyiv                   max_kyiv empty unparseable
started_at   2022-03-15 16:10:34+00:00  2026-09-07 05:28:22+00:00  2022-03-15 18:10:34+02:00  2026-09-07 08:28:22+03:00     0           0
finished_at  2022-03-15 16:50:07+00:00  2026-09-07 05:39:33+00:00  2022-03-15 18:50:07+02:00  2026-09-07 08:39:33+03:00     0           0
```
duration in minutes (finished_at - started_at), repeated copies removed:
```
count    185430.0
mean        135.7
std        2518.2
min           0.0
1%            5.3
50%          48.9
90%         284.9
99%        1129.9
max      869836.5
```
duration <= 0: 2; > 24 h: 897; > 7 days: 13
10 longest alerts (repeated copies removed):
```
                        oblast              raion                                   hromada    level                started_at               finished_at    hours
44603        Kharkivska oblast  Kharkivskyi raion             Lypetska terytorialna hromada  hromada 2024-05-12 08:37:29+00:00 2026-01-06 09:53:57+00:00  14497.3
45324        Kharkivska oblast  Chuhuivskyi raion           Vovchanska terytorialna hromada  hromada 2024-05-20 09:31:41+00:00 2025-08-01 22:52:43+00:00  10525.4
296882         Donetska oblast   Pokrovskyi raion            Pokrovska terytorialna hromada  hromada 2026-07-26 14:38:44+00:00 2026-08-29 04:17:56+00:00    805.7
252076  Dnipropetrovska oblast  Nikopolskyi raion  Chervonohryhorivska terytorialna hromada  hromada 2026-03-23 21:53:07+00:00 2026-04-19 05:12:29+00:00    631.3
64679   Dnipropetrovska oblast  Nikopolskyi raion             Myrivska terytorialna hromada  hromada 2025-02-24 14:01:55+00:00 2025-03-17 03:07:56+00:00    493.1
243760  Dnipropetrovska oblast  Nikopolskyi raion  Chervonohryhorivska terytorialna hromada  hromada 2026-03-03 20:50:20+00:00 2026-03-23 17:54:21+00:00    477.1
61721   Dnipropetrovska oblast  Nikopolskyi raion             Myrivska terytorialna hromada  hromada 2025-01-12 07:37:02+00:00 2025-01-25 06:46:14+00:00    311.2
67440   Dnipropetrovska oblast  Nikopolskyi raion             Myrivska terytorialna hromada  hromada 2025-04-07 10:50:26+00:00 2025-04-20 05:27:01+00:00    306.6
237379  Dnipropetrovska oblast  Nikopolskyi raion  Chervonohryhorivska terytorialna hromada  hromada 2026-02-21 09:46:42+00:00 2026-03-02 17:20:09+00:00    223.6
233111  Dnipropetrovska oblast  Nikopolskyi raion  Chervonohryhorivska terytorialna hromada  hromada 2026-02-05 20:08:27+00:00 2026-02-14 07:37:42+00:00    203.5
```
alerts longer than 24 h, by oblast and level:
```
level                   hromada  oblast  raion  All
oblast                                             
Chernihivska oblast           0       2     10   12
Dnipropetrovska oblast      362       0     24  386
Donetska oblast              29       3    360  392
Kharkivska oblast             3       5     10   18
Kirovohradska oblast          0       0      3    3
Kyivska oblast                0       0      4    4
Luhanska oblast               0       1      0    1
Sumska oblast                 0       2     10   12
Zakarpatska oblast            0       0      2    2
Zaporizka oblast              2       0     65   67
All                         396      13    488  897
```

## 3. Values: alert levels and region names (repeated copies removed)

level value counts:
```
level
raion      99304
oblast     65314
hromada    20812
```
25 distinct oblast values (rows, first/last day seen in Kyiv time, rows per level):
```
                          rows  first_seen   last_seen  hromada  oblast  raion
oblast                                                                        
Cherkaska oblast          6290  2022-03-15  2026-09-06       43    2459   3788
Chernihivska oblast       9854  2022-03-15  2026-09-06        0    2513   7341
Chernivetska oblast       1081  2022-03-17  2026-09-05        0     747    334
Dnipropetrovska oblast   27495  2022-03-15  2026-09-07     9987    5565  11943
Donetska oblast          16609  2022-03-15  2026-09-07     2820    6877   6912
Ivano-Frankivska oblast   1306  2022-03-15  2026-08-07        0     742    564
Kharkivska oblast        25810  2022-03-16  2026-09-07     3603    6504  15703
Khersonska oblast         7898  2022-03-27  2026-09-06        4    3575   4319
Khmelnytska oblast        1631  2022-03-15  2026-09-05       21    1030    580
Kirovohradska oblast      7187  2022-03-15  2026-09-06        0    3344   3843
Kyiv City                 2267  2022-03-15  2026-09-06        0    2267      0
Kyivska oblast            6977  2022-03-15  2026-09-06       88    1950   4939
Luhanska oblast              1  2022-03-24  2022-03-24        0       1      0
Lvivska oblast            1408  2022-03-15  2026-08-07        0     745    663
Mykolaivska oblast        9348  2022-03-15  2026-09-07     1671    3681   3996
Odeska oblast             9043  2022-03-16  2026-09-07        1    2411   6631
Poltavska oblast          9803  2022-03-15  2026-09-07       68    3993   5742
Rivnenska oblast          1593  2022-03-15  2026-09-05        4     892    697
Sumska oblast            13547  2022-03-15  2026-09-07       16    4078   9453
Ternopilska oblast        1187  2022-03-15  2026-09-03        0     842    345
Vinnytska oblast          3133  2022-03-15  2026-09-05        0    1482   1651
Volynska oblast           1239  2022-03-15  2026-09-05        0     800    439
Zakarpatska oblast        1200  2022-03-17  2026-08-07        0     664    536
Zaporizka oblast         16612  2022-03-16  2026-09-07     2417    6686   7509
Zhytomyrska oblast        2911  2022-03-15  2026-09-05       69    1466   1376
```
distinct raion values: 118
distinct hromada values: 133

## 4. Collapse test: alert rows by level over time (repeated copies removed; Kyiv time of start)

rows per month by level, last 18 months (last month partial; full table: reports/monthly_counts_by_level.csv):
```
         hromada  oblast  raion  total  repeated_copies_removed
month                                                          
2025-04      641    1496     91   2228                     2228
2025-05      597    1354    317   2268                     2268
2025-06      631    1455    341   2427                     2427
2025-07      696    1776    588   3060                     3060
2025-08      631    1118   2429   4178                     4178
2025-09      570     704   3463   4737                     4737
2025-10      695     716   3512   4923                     4915
2025-11      705     165   7219   8089                     8053
2025-12      694      24   7340   8058                     8034
2026-01      705      58   7663   8426                     6968
2026-02      538      41   7351   7930                        0
2026-03      799      39   8908   9746                        0
2026-04      689      35   7889   8613                        0
2026-05      649      58   9378  10085                        0
2026-06      664      46   9301  10011                        0
2026-07      637      58  10349  11044                        0
2026-08      565      91  10029  10685                        0
2026-09       88      22   1827   1937                        0
```
days with zero alert rows at all levels, 2022-03-15 .. 2026-09-07: 3
  2026-08-30, 2026-08-31, 2026-09-01
rows per day by level, last 60 days (full table: reports/daily_counts_by_level.csv):
```
level           hromada  oblast  raion  total
day                                          
2026-07-10 Fri       21       0    334    355
2026-07-11 Sat       22       1    365    388
2026-07-12 Sun       19       0    237    256
2026-07-13 Mon       24       0    307    331
2026-07-14 Tue       23       3    414    440
2026-07-15 Wed       25       2    341    368
2026-07-16 Thu       28       1    443    472
2026-07-17 Fri       21       2    418    441
2026-07-18 Sat       20       2    372    394
2026-07-19 Sun       18       4    408    430
2026-07-20 Mon       23       1    323    347
2026-07-21 Tue       19       2    254    275
2026-07-22 Wed        9       2    326    337
2026-07-23 Thu       30       1    458    489
2026-07-24 Fri       19       5    358    382
2026-07-25 Sat       19       3    419    441
2026-07-26 Sun       21       2    346    369
2026-07-27 Mon       21       4    370    395
2026-07-28 Tue       19       1    277    297
2026-07-29 Wed       20       0    305    325
2026-07-30 Thu       19       1    359    379
2026-07-31 Fri       21       4    380    405
2026-08-01 Sat       22       3    364    389
2026-08-02 Sun       18       3    323    344
2026-08-03 Mon       18       1    344    363
2026-08-04 Tue       23       3    372    398
2026-08-05 Wed       16       3    351    370
2026-08-06 Thu       20       1    283    304
2026-08-07 Fri       25       2    391    418
2026-08-08 Sat       20       4    302    326
2026-08-09 Sun       18       0    333    351
2026-08-10 Mon       20       4    480    504
2026-08-11 Tue       25       3    393    421
2026-08-12 Wed       22       3    416    441
2026-08-13 Thu       22       0    286    308
2026-08-14 Fri       19       0    237    256
2026-08-15 Sat       21       0    242    263
2026-08-16 Sun       21       5    336    362
2026-08-17 Mon       17       1    238    256
2026-08-18 Tue       16      10    351    377
2026-08-19 Wed       19       0    249    268
2026-08-20 Thu       22       7    362    391
2026-08-21 Fri       22       0    273    295
2026-08-22 Sat       13       5    392    410
2026-08-23 Sun       25       1    296    322
2026-08-24 Mon       21       2    401    424
2026-08-25 Tue       17       1    400    418
2026-08-26 Wed       11       1    372    384
2026-08-27 Thu       26      13    568    607
2026-08-28 Fri       24      12    506    542
2026-08-29 Sat        2       3    168    173
2026-08-30 Sun        0       0      0      0
2026-08-31 Mon        0       0      0      0
2026-09-01 Tue        0       0      0      0
2026-09-02 Wed        7       2    160    169
2026-09-03 Thu       23       7    453    483
2026-09-04 Fri       20       7    405    432
2026-09-05 Sat       17       5    399    421
2026-09-06 Sun       16       1    347    364
2026-09-07 Mon        5       0     63     68
```
% of each oblast's rows that are NOT oblast-level (raion/hromada), by month since 2025-07; last column = first month since 2025-01 with >= 50%:
```
                         25-07  25-08  25-09  25-10  25-11  25-12  26-01  26-02  26-03  26-04  26-05  26-06  26-07  26-08  26-09 first>=50%
oblast                                                                                                                                     
Cherkaska oblast            61     46     76     78     94    100    100    100    100    100    100    100    100    100    100    2025-01
Chernihivska oblast          0     47    100     99    100    100    100    100    100    100    100    100    100    100    100    2025-09
Chernivetska oblast          0      0      0      0     98    100    100    100    100    100    100    100    100    100    100    2025-11
Dnipropetrovska oblast      89     85     92     94     99    100    100    100    100    100    100    100    100    100    100    2025-01
Donetska oblast             55     49     59     67     98    100    100    100    100    100    100    100    100    100    100    2025-06
Ivano-Frankivska oblast      0      0      0      0     99    100    100    100    100    100    100    100    100    100   <NA>    2025-11
Kharkivska oblast           45     95    100     99    100    100    100    100    100    100    100    100    100    100    100    2025-08
Khersonska oblast            0     29     30     54     96    100    100    100    100    100    100    100    100    100    100    2025-10
Khmelnytska oblast          50     69    100    100    100    100    100    100    100    100    100    100    100    100    100    2025-07
Kirovohradska oblast         0     42     97     93     99    100    100    100    100    100    100    100    100    100    100    2025-09
Kyiv City                    0      0      0      0      0      0      0      0      0      0      0      0      0      0      0          -
Kyivska oblast              59     95     99     94     97    100    100    100    100    100    100    100    100    100    100    2025-07
Luhanska oblast           <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>   <NA>          -
Lvivska oblast               0      0     59      8     99    100    100    100    100    100    100    100    100    100   <NA>    2025-09
Mykolaivska oblast           0      0      0      0     95    100    100    100    100    100    100    100    100    100    100    2025-11
Odeska oblast                0      0      1      0     98    100    100    100    100    100    100    100    100    100    100    2025-11
Poltavska oblast             0     97    100     99    100    100    100    100    100    100    100    100    100    100    100    2025-08
Rivnenska oblast             0     50     84     84    100    100    100    100    100    100    100    100    100    100    100    2025-08
Sumska oblast                0     89    100    100    100    100    100    100    100    100    100    100    100    100    100    2025-08
Ternopilska oblast           0      0      0      0     98    100    100    100    100    100    100    100    100    100    100    2025-11
Vinnytska oblast             0     47     60     67     98    100    100    100    100    100    100    100    100    100    100    2025-09
Volynska oblast              0      0      0      0     97    100    100    100    100    100    100    100    100    100    100    2025-11
Zakarpatska oblast           0      0      0      0     99    100    100    100    100    100    100    100    100    100   <NA>    2025-11
Zaporizka oblast            43     42     40     43     97    100    100    100    100    100    100    100    100    100    100    2025-11
Zhytomyrska oblast           0      0      0     50     97    100    100    100    100    100    100    100    100    100    100    2025-10
```
figure: reports/fig_daily_counts_by_level.png

## 5. Official file: how fresh and how complete is the tail?

dataset commit: 2026-10-12T05:05:17Z = 2026-10-12 08:05 Kyiv
official file: latest started_at 2026-09-07 08:28 Kyiv, latest finished_at 2026-09-07 08:39 Kyiv = 35 days before the commit date
official file: gaps of >= 8 h between consecutive alert starts since 2025-01-01 (Kyiv time): 4; largest 4:
```
        gap_hours last_start_before_gap next_start_after_gap
297333      104.9      2026-08-29 07:55     2026-09-02 16:48
68452        19.1      2025-04-19 21:52     2025-04-20 16:56
65180         8.7      2025-03-03 23:34     2025-03-04 08:16
64047         8.1      2025-02-15 01:45     2025-02-15 09:48
```
days since 2025-01-01 with fewer than half the rows of the previous-28-day median (outage, or a partial day at the start/end of an outage or of the file):
```
                rows  oblasts_with_alerts  prev28_median_rows  ratio
2025-01-07 Tue    31                    7                63.0   0.49
2025-02-03 Mon    30                   11                61.5   0.49
2025-02-15 Sat    32                   12                67.0   0.48
2025-04-20 Sun     3                    1                65.0   0.05
2025-05-08 Thu    39                   11                79.5   0.49
2025-05-09 Fri    21                    6                75.0   0.28
2025-05-10 Sat    32                    5                75.0   0.43
2025-11-30 Sun   127                   11               261.0   0.49
2025-12-28 Sun   118                    9               247.0   0.48
2026-04-12 Sun   106                    5               301.0   0.35
2026-05-09 Sat   120                    6               294.0   0.41
2026-05-10 Sun   115                    7               294.0   0.39
2026-05-11 Mon   108                    6               294.0   0.37
2026-08-29 Sat   173                   15               373.5   0.46
2026-08-30 Sun     0                    0               366.5   0.00
2026-08-31 Mon     0                    0               366.5   0.00
2026-09-01 Tue     0                    0               366.0   0.00
2026-09-02 Wed   169                   18               356.5   0.47
2026-09-07 Mon    68                    8               370.5   0.18
```
last 7 days of the official file:
```
                rows  oblasts_with_alerts
2026-09-01 Tue     0                    0
2026-09-02 Wed   169                   18
2026-09-03 Thu   483                   21
2026-09-04 Fri   432                   17
2026-09-05 Sat   421                   20
2026-09-06 Sun   364                   14
2026-09-07 Mon    68                    8
```

## 6. Volunteer file, and how well it matches the official file where they overlap

shape: (116174, 4); columns: ['region', 'started_at', 'finished_at', 'naive']
```
             region                 started_at                finished_at  naive
0         Kyiv City  2022-02-25 16:36:22+00:00  2022-02-25 17:06:22+00:00   True
1  Cherkaska oblast  2022-02-25 18:36:21+00:00  2022-02-25 19:32:11+00:00  False
2  Rivnenska oblast  2022-02-25 18:56:44+00:00  2022-02-25 19:26:44+00:00   True
```
started_at range: 2022-02-25 18:36 .. 2026-10-12 07:49 Kyiv (unparseable: 0); latest finished_at 2026-10-12 07:59 Kyiv
exact duplicate rows: 0; empty values per column: region=0, started_at=0, finished_at=0, naive=0
rows per month and share of 'naive' rows (end unknown, finished_at = started_at + 30 min), last 24 months:
```
         rows  naive_share
month                     
2024-11  1887         0.10
2024-12  1773         0.10
2025-01  1950         0.07
2025-02  1737         0.05
2025-03  1715         0.07
2025-04  1805         0.06
2025-05  1769         0.07
2025-06  1837         0.06
2025-07  2245         0.06
2025-08  2154         0.05
2025-09  2168         0.05
2025-10  2291         0.06
2025-11  2505         0.05
2025-12  2464         0.05
2026-01  2784         0.05
2026-02  2558         0.05
2026-03  3343         0.03
2026-04  3001         0.04
2026-05  3402         0.04
2026-06  3298         0.04
2026-07  3408         0.05
2026-08  3906         0.04
2026-09  4449         0.06
2026-10  1793         0.10
```
rows per day, last 14 days (the last day is partial):
```
            rows  naive_rows
day                         
2026-09-29   156          11
2026-09-30   155          16
2026-10-01   139          13
2026-10-02   158          14
2026-10-03   132          16
2026-10-04   130          12
2026-10-05   141          19
2026-10-06   155          12
2026-10-07   157          15
2026-10-08   147          17
2026-10-09   192          11
2026-10-10   198          20
2026-10-11   189          20
2026-10-12    55           3
```
alert duration in minutes (finished_at - started_at):
```
       all rows  not naive
count  116174.0   110340.0
mean       47.7       48.7
std        85.1       87.2
min         0.0        0.0
1%          0.8        0.8
50%        30.0       31.1
90%       103.8      106.7
99%       266.0      270.3
max     10695.9    10695.9
```
duration <= 0: 6; > 24 h: 14; > 7 days: 2
volunteer file: gaps of >= 8 h between consecutive alert starts since 2025-01-01 (Kyiv time): 0; largest 0:
```
Empty DataFrame
Columns: [gap_hours, last_start_before_gap, next_start_after_gap]
Index: []
```
25 volunteer regions. Only in the volunteer file: []; only in the official file: []
```
                          rows  first_seen   last_seen
region                                                
Cherkaska oblast          3894  2022-02-25  2026-10-12
Chernihivska oblast       5613  2022-02-26  2026-10-12
Chernivetska oblast        917  2022-02-27  2026-10-12
Dnipropetrovska oblast   13752  2022-02-27  2026-10-12
Donetska oblast           8549  2022-02-27  2026-10-12
Ivano-Frankivska oblast    895  2022-02-27  2026-10-11
Kharkivska oblast        13001  2022-02-26  2026-10-12
Khersonska oblast         6434  2022-02-26  2026-10-12
Khmelnytska oblast        1366  2022-02-26  2026-10-11
Kirovohradska oblast      6339  2022-02-27  2026-10-12
Kyiv City                 2673  2022-02-25  2026-10-11
Kyivska oblast            4471  2022-02-27  2026-10-12
Luhanska oblast              3  2022-02-28  2022-04-04
Lvivska oblast            1798  2022-02-26  2026-10-12
Mykolaivska oblast        7899  2022-02-26  2026-10-12
Odeska oblast             4597  2022-02-26  2026-10-12
Poltavska oblast          6569  2022-02-27  2026-10-12
Rivnenska oblast          1286  2022-02-25  2026-10-12
Sumska oblast             8744  2022-02-26  2026-10-12
Ternopilska oblast        1015  2022-02-26  2026-10-12
Vinnytska oblast          2093  2022-02-25  2026-10-12
Volynska oblast           2205  2022-02-25  2026-10-12
Zakarpatska oblast         761  2022-03-12  2026-07-30
Zaporizka oblast          8973  2022-02-25  2026-10-12
Zhytomyrska oblast        2327  2022-02-26  2026-10-12
```
official vs volunteer, daily, Kyiv date of start (official with repeated copies removed):
```
                                            2024 (before the switch)  2025-01..06 (before the switch)  2026-03-01..08-28 (after the switch, before the outage)
days                                                          366.00                           181.00                                                   181.00
official rows/day, all levels                                  71.40                            71.40                                                   331.60
official rows/day, oblast level                                59.10                            48.90                                                     1.80
volunteer rows/day                                             69.20                            59.70                                                   109.70
official: oblasts with an alert start/day                      18.00                            16.70                                                    16.50
volunteer: regions with an alert start/day                     18.30                            17.10                                                    17.90
daily correlation of those two counts                           0.99                             0.94                                                     0.96
```
