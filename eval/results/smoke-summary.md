## Eval: smoke (20 points)

| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|---|
| raw | all | 20 | 40.0 | 62.1 | 90.0 | 85 | 383 |
| raw | line | 12 | 58.3 | 69.1 | 91.7 | 75 | 172 |
| raw | block | 8 | 12.5 | 51.5 | 87.5 | 142 | 383 |
| +cleanup | all | 20 | 40.0 | 57.4 | 80.0 | 85 | 383 |
| +cleanup | line | 12 | 50.0 | 60.8 | 83.3 | 75 | 172 |
| +cleanup | block | 8 | 25.0 | 52.2 | 75.0 | 142 | 383 |
| +context | all | 20 | 40.0 | 59.4 | 90.0 | 46 | 276 |
| +context | line | 12 | 50.0 | 63.1 | 91.7 | 23 | 94 |
| +context | block | 8 | 25.0 | 53.7 | 87.5 | 98 | 293 |

Points that had a cheat sheet only:

| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|
| +cleanup | 1 | 0.0 | 7.5 | 0.0 | 61 | 61 |
| +context | 1 | 0.0 | 35.8 | 100.0 | 94 | 94 |
