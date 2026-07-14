# Community Schema scalable benchmark results

In-memory model of the Community Schema AQL under three access patterns (`baseline`, `C`, `A2_B_D`). Times are wall-clock Python microseconds→ms on synthetic data; relative trends matter more than absolute values.

| n_docs | strategy | matches | inspected | full_fetches | approx_bytes | median_ms | p95_ms |
|-------:|----------|--------:|----------:|-------------:|-------------:|----------:|-------:|
| 1000 | baseline | 79 | 158 | 158 | 647168 | 0.030 | 0.043 |
| 1000 | C | 79 | 79 | 79 | 323584 | 0.013 | 0.030 |
| 1000 | A2_B_D | 79 | 79 | 0 | 5056 | 0.009 | 0.015 |
| 5000 | baseline | 357 | 736 | 736 | 3014656 | 0.100 | 0.178 |
| 5000 | C | 357 | 357 | 357 | 1462272 | 0.056 | 0.118 |
| 5000 | A2_B_D | 357 | 357 | 0 | 22848 | 0.040 | 0.044 |
| 10000 | baseline | 726 | 1426 | 1426 | 5840896 | 0.194 | 0.369 |
| 10000 | C | 726 | 726 | 726 | 2973696 | 0.114 | 0.247 |
| 10000 | A2_B_D | 726 | 726 | 0 | 46464 | 0.077 | 0.083 |
| 50000 | baseline | 3666 | 7349 | 7349 | 30101504 | 1.984 | 2.645 |
| 50000 | C | 3666 | 3666 | 3666 | 15015936 | 1.175 | 1.801 |
| 50000 | A2_B_D | 3666 | 3666 | 0 | 234624 | 0.651 | 0.663 |
| 100000 | baseline | 7413 | 14968 | 14968 | 61308928 | 3.972 | 5.981 |
| 100000 | C | 7413 | 7413 | 7413 | 30363648 | 2.519 | 3.824 |
| 100000 | A2_B_D | 7413 | 7413 | 0 | 474432 | 1.402 | 1.458 |
| 250000 | baseline | 18604 | 37295 | 37295 | 152760320 | 10.264 | 14.309 |
| 250000 | C | 18604 | 18604 | 18604 | 76201984 | 7.100 | 10.368 |
| 250000 | A2_B_D | 18604 | 18604 | 0 | 1190656 | 3.893 | 4.298 |

## Speedup vs baseline (median_ms)

| n_docs | C / baseline | A2_B_D / baseline | bytes A2_B_D / baseline |
|-------:|-------------:|------------------:|------------------------:|
| 1000 | 2.34x | 3.25x | 0.0078 |
| 5000 | 1.79x | 2.53x | 0.0076 |
| 10000 | 1.70x | 2.53x | 0.0080 |
| 50000 | 1.69x | 3.05x | 0.0078 |
| 100000 | 1.58x | 2.83x | 0.0077 |
| 250000 | 1.45x | 2.64x | 0.0078 |

## Observations

- **baseline** inspects every community in the selected partitions (level filter after index probe) and fetches full fat documents.
- **C** inspects only `level <= max` via the composite index, but still fetches full documents for `occurrence`.
- **A2/B/D** uses covering `storedValues`, so inspected rows stay low and full document fetches stay at **0** — bytes read scales with matches, not partition size × payload.
