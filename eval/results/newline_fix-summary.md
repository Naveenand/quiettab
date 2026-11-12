## Eval: newline_fix (250 points)

| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|---|
| raw | all | 250 | 24.8 | 54.1 | 90.4 | 82 | 276 |
| raw | line | 150 | 38.0 | 60.1 | 98.7 | 62 | 111 |
| raw | block | 100 | 5.0 | 45.0 | 78.0 | 175 | 309 |
| +cleanup | all | 250 | 25.6 | 52.2 | 96.4 | 82 | 276 |
| +cleanup | line | 150 | 38.0 | 60.1 | 98.7 | 62 | 111 |
| +cleanup | block | 100 | 7.0 | 40.3 | 93.0 | 175 | 309 |
| +context | all | 250 | 25.6 | 51.9 | 96.4 | 62 | 265 |
| +context | line | 150 | 38.0 | 60.3 | 99.3 | 40 | 91 |
| +context | block | 100 | 7.0 | 39.4 | 92.0 | 148 | 287 |

Points that had a cheat sheet only:

| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|
| +cleanup | 32 | 6.2 | 38.7 | 96.9 | 77 | 240 |
| +context | 32 | 6.2 | 38.9 | 96.9 | 85 | 299 |
