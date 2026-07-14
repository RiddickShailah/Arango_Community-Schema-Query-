# Work log

## 2026-07-14

### Understood the problem
- Mapped Community Schema AQL filters/return fields to Communities document shape.
- Confirmed importer currently creates only `partition_id_index` on `["partition_id"]` for all collections when `partition_id` is set.
- Confirmed `create_persistent_index` has no `storedValues` support yet.
- Clarified ownership: latency in retriever; index creation in graphrag_importer.

### Brainstormed solutions
- Documented options A–F (Communities-only composite, data-driven specs, no storedValues, migration, retriever-side, all-collections).
- Prefer **A2** (or **B**), with `storedValues=["occurrence"]`, drop old Communities `partition_id_index`, keep other collections as-is.
- Flagged existence-check field-order issue and migration for existing DBs.

### Tracking repo
- Initialized this repository with organized docs:
  - `README.md` — map of the work
  - `docs/01-problem.md`
  - `docs/02-solutions.md`
  - `docs/03-recommendation.md`
  - `docs/04-code-touchpoints.md`
  - `WORKLOG.md` — this file

### Next
- Pick A2 vs B and implement in graphrag_importer.
- Add unit/integration coverage.
- Decide if existing-DB migration is in scope.

### Tracking repo push blocked
- Commit created locally: `e770e97` on `main`.
- `git push` to `RiddickShailah/Arango_Community-Schema-Query-` failed with HTTP 403 (`cursor[bot]` has no write access).
- Notes are ready to push from this clone once write access is granted, or via the export archive.

## 2026-07-14 (continued) — implement & test all solutions

Implemented strategies baseline/A1/A2/B/C/D/E/F as pure plans in
`graphrag/importer/partition_index_strategies.py`, wired production path to **B**
(equals A2), added Option D migration script, and evaluated with a 7-check rubric.

### Pytest
- `17 passed` — `tests/unit/test_partition_index_strategies.py`

### Scores
| Strategy | Score | Result |
|----------|-------|--------|
| baseline | 3/7 | FAIL |
| A1 | 6/7 | FAIL (redundant index) |
| A2 | 7/7 | PASS |
| B | 7/7 | PASS (production) |
| C | 6/7 | FAIL (no storedValues) |
| D | 7/7 | PASS (A2 + migration) |
| E | 1/7 | FAIL in importer scope |
| F | 5/7 | FAIL (wrong collections) |

See `results/strategy_comparison.md`.

## 2026-07-14 — scalable multi-size benchmarks

Added in-memory Community Schema scale bench and ran:
- pytest: 24 passed (strategy + scale suites)
- scales: 1k, 5k, 10k, 50k, 100k, 250k communities (20 partitions, query 3 partitions, level<=2, 7 rounds)

Key finding at 250k docs (median):
- baseline 10.264ms, 37295 full fetches, ~152MB approx bytes
- C 7.100ms, 18604 full fetches
- A2/B/D 3.893ms, 0 full fetches, ~1.2MB approx bytes (~128x less bytes than baseline)

Artifacts: `results/scale_bench/`

## 2026-07-14 — decision documented

Recorded accepted solution **B (= A2)** in graphrag_importer:
`docs/community_schema_index_decision.md` (mirrored here as `docs/05-decision.md`).

## 2026-07-14 — semi-live ArangoDB validation

Local ArangoDB 3.12.4 (auth off). Solution B applied via strategy planner.

| Docs | baseline median | B median | Speedup | Index used |
|------|----------------:|---------:|--------:|------------|
| 50k | 18.63 ms | 13.86 ms | 1.34× | partition_id_level_index |
| 150k | 55.40 ms | 36.92 ms | 1.50× | partition_id_level_index |

storedValues=["occurrence"] confirmed; result counts matched; pytest semi-live passed.

## 2026-07-14 — full report + PowerPoint

Added stakeholder pack:
- Full report covering problem → brainstorm → decision → tests → semi-live
- 13-slide PowerPoint (slate/teal deck)
Mirrored under docs/ in this tracking repo.
