## Eval: realfim (300 points)

| setup | kind | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|---|
| raw | all | 300 | 2.0 | 31.6 | 70.3 | 219 | 309 |
| raw | line | 86 | 4.7 | 32.6 | 72.1 | 281 | 306 |
| raw | block | 214 | 0.9 | 31.1 | 69.6 | 192 | 309 |
| +cleanup | all | 300 | 2.0 | 24.9 | 79.3 | 219 | 309 |
| +cleanup | line | 86 | 4.7 | 29.8 | 77.9 | 281 | 306 |
| +cleanup | block | 214 | 0.9 | 23.0 | 79.9 | 192 | 309 |
| +context | all | 300 | 1.7 | 24.5 | 77.7 | 172 | 273 |
| +context | line | 86 | 3.5 | 29.3 | 75.6 | 246 | 278 |
| +context | block | 214 | 0.9 | 22.6 | 78.5 | 149 | 271 |

Points that had a cheat sheet only:

| setup | n | exact match % | chrF | valid code % | p50 ms | p90 ms |
|---|---|---|---|---|---|---|
