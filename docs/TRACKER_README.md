# Arango Community Schema Query

Personal tracker for the **Community Schema** index ticket in `graphrag_importer`.

## Ticket goal

Speed up:

```aql
FOR c IN @@communities_collection
  FILTER c.partition_id IN @partition_ids
  FILTER c.level <= @level
  RETURN { _key, level, occurrence }
```

via Communities index `partition_id_level_index` on `(partition_id, level)` with `storedValues: ["occurrence"]`.

## Status

- [x] Implement in importer (solution B = A2)
- [x] Unit + integration CI green
- [x] Pilot AQL EXPLAIN/profile
- [x] Pilot retriever Q1 (global) + Q2 (local)
- [ ] Merge PR #228 → US DEV verify + re-time

**PR:** https://github.com/arangoml/graphrag_importer/pull/228  
**Commit / DEV image:** `ae18835` · `v0.0.30-ae18835`

## Findings (headline)

| Layer | Result |
|-------|--------|
| Index works on Pilot | EXPLAIN → `partition_id_level_index` + stored `occurrence` |
| Community Schema AQL | **~3.4 ms** (525 rows, `default_1_a`, level ≤ 2) |
| Semi-live earlier | **1.34×–1.50×** vs baseline |
| Global Q1 E2E | **~24.1 s** wall (LLM-bound) |
| Local Q2 E2E | **~5.9 s** wall |
| Partition hygiene | `NV_Bugs` had null `partition_id` — used `test_deep_search` |

**Takeaway:** Index fixes the **AQL** path. Full retriever times are mostly **LLM-bound** — report both separately.

## Docs / pack

| Doc | Purpose |
|-----|---------|
| [`docs/09-findings-summary.md`](docs/09-findings-summary.md) | One-pager |
| [`docs/08-pilot-retriever-findings.md`](docs/08-pilot-retriever-findings.md) | Full Pilot + E2E findings |
| [`docs/10-mentor-update.md`](docs/10-mentor-update.md) | Short note to send mentor |
| [`docs/community_schema_us_dev_build_request.md`](docs/community_schema_us_dev_build_request.md) | US DEV deploy + timing table |
| [`docs/interactive/index.html`](docs/interactive/index.html) | Interactive slideshow + graphs |
| [`docs/Community_Schema_Optimization.pptx`](docs/Community_Schema_Optimization.pptx) | PowerPoint |
| [`docs/06-full-report.md`](docs/06-full-report.md) | Earlier full narrative |

```bash
# Open slideshow
open docs/interactive/index.html

# Regenerate deck
python3 scripts/generate_stakeholder_pack.py
```
