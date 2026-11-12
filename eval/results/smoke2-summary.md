## Eval: smoke2 (20 points)

| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|---|
| raw | all | 20 | 40.0 | 60.9 | 90.0 | 82 | 328 |
| raw | line | 12 | 58.3 | 69.1 | 91.7 | 70 | 140 |
| raw | block | 8 | 12.5 | 48.7 | 87.5 | 150 | 328 |
| +cleanup | all | 20 | 45.0 | 62.3 | 95.0 | 82 | 328 |
| +cleanup | line | 12 | 58.3 | 69.1 | 91.7 | 70 | 140 |
| +cleanup | block | 8 | 25.0 | 52.1 | 100.0 | 150 | 328 |
| +context | all | 20 | 45.0 | 63.7 | 100.0 | 45 | 270 |
| +context | line | 12 | 58.3 | 71.5 | 100.0 | 22 | 79 |
| +context | block | 8 | 25.0 | 52.1 | 100.0 | 98 | 272 |

Points that had a cheat sheet only:

| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|
| +cleanup | 1 | 0.0 | 7.5 | 0.0 | 43 | 43 |
| +context | 1 | 0.0 | 35.8 | 100.0 | 79 | 79 |
