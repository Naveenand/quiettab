## Eval: debug_run (250 points)

| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|---|
| raw | all | 250 | 24.8 | 54.1 | 90.4 | 104 | 295 |
| raw | line | 150 | 38.0 | 60.1 | 98.7 | 79 | 133 |
| raw | block | 100 | 5.0 | 45.1 | 78.0 | 186 | 333 |
| +cleanup | all | 250 | 25.6 | 52.2 | 96.4 | 104 | 295 |
| +cleanup | line | 150 | 38.0 | 60.1 | 98.7 | 79 | 133 |
| +cleanup | block | 100 | 7.0 | 40.3 | 93.0 | 186 | 333 |
| +context | all | 250 | 25.6 | 51.6 | 96.8 | 64 | 268 |
| +context | line | 150 | 38.0 | 59.7 | 99.3 | 42 | 93 |
| +context | block | 100 | 7.0 | 39.5 | 93.0 | 157 | 290 |

Points that had a cheat sheet only:

| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|
| +cleanup | 32 | 6.2 | 38.7 | 96.9 | 95 | 269 |
| +context | 32 | 6.2 | 36.4 | 100.0 | 83 | 303 |
