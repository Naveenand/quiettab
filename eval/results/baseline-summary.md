## Eval: baseline (250 points)

| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|---|
| raw | all | 250 | 24.4 | 54.1 | 90.8 | 93 | 291 |
| raw | line | 150 | 37.3 | 60.4 | 99.3 | 68 | 116 |
| raw | block | 100 | 5.0 | 44.7 | 78.0 | 181 | 313 |
| +cleanup | all | 250 | 25.2 | 52.1 | 97.6 | 93 | 291 |
| +cleanup | line | 150 | 37.3 | 60.4 | 99.3 | 68 | 116 |
| +cleanup | block | 100 | 7.0 | 39.5 | 95.0 | 181 | 313 |
| +context | all | 250 | 25.2 | 51.9 | 97.2 | 59 | 270 |
| +context | line | 150 | 37.3 | 59.6 | 100.0 | 40 | 89 |
| +context | block | 100 | 7.0 | 40.5 | 93.0 | 161 | 290 |

Points that had a cheat sheet only:

| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|
| +cleanup | 32 | 6.2 | 40.1 | 96.9 | 93 | 256 |
| +context | 32 | 6.2 | 36.9 | 100.0 | 69 | 304 |
