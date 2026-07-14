# Community Schema Query Optimization — Full Project Report

**Project:** Optimize Community Schema retriever latency via composite persistent index in `graphrag_importer`  
**Date:** 2026-07-14  
**Status:** Implemented, tested (unit + scale + semi-live), decision documented  
**PR:** https://github.com/arangoml/graphrag_importer/pull/227  
**Accepted solution:** **B** (data-driven specs) with **A2** behavior  
**Slide deck:** [`community_schema_optimization_deck.pptx`](community_schema_optimization_deck.pptx)

---

## 1. Executive summary

The Community Schema AQL path in the retriever contributes meaningfully to latency. It filters Communities by `partition_id` and `level`, then returns `_key`, `level`, and `occurrence`. The importer previously created only a single-field persistent index (`partition_id_index` on `partition_id`).

We analyzed the problem, brainstormed solutions A–F, implemented them as comparable index plans, chose **B (= A2)**, wired it into production initialization, validated with unit tests, multi-scale synthetic benches, and a **semi-live ArangoDB 3.12.4** run. On real AQL:

| Scale | Baseline median | Solution B median | Speedup |
|------:|----------------:|------------------:|--------:|
| 50k communities | 18.63 ms | 13.86 ms | **1.34×** |
| 150k communities | 55.40 ms | 36.92 ms | **1.50×** |

ArangoDB’s EXPLAIN selected `partition_id_level_index` after applying B. Result counts matched baseline exactly.

---

## 2. Problem statement

### 2.1 Ticket summary

Optimize the Community Schema query by adding a composite persistent index on `(partition_id, level)` with stored values in `graphrag_importer`.

### 2.2 Hot query (retriever)

```aql
FOR c IN @@communities_collection
    FILTER c.partition_id IN @partition_ids
    FILTER c.level <= @level
    RETURN {
        _key: c._key,
        level: c.level,
        occurrence: c.occurrence
    }
```

### 2.3 Why it was slow

1. **Partition-only index** — `partition_id_index` narrows by partition, then `level <= @level` is evaluated on candidates.
2. **Fat documents** — Community docs carry `report_string`, `report_json`, embeddings, etc. Returning `occurrence` without a covering index tends to materialize full documents.
3. **Ownership split** — latency shows up in the **retriever**; indexes are created at **import / graph init** in **graphrag_importer**. Fixing the importer is required for lasting product behavior.

### 2.4 Proposed index (from ticket)

```js
db._collection("nvbugs_b1_Communities").ensureIndex({
  type: "persistent",
  fields: ["partition_id", "level"],
  storedValues: ["occurrence"],
  name: "partition_id_level_index",
  inBackground: true
});
```

### 2.5 Domain context

GraphRAG Communities are hierarchical clusters of related entities:

| Field | Role |
|-------|------|
| `partition_id` | Logical partition (AutoGraph RAG partition / standalone batch); many partitions share one collection |
| `level` | Hierarchical Leiden community level |
| `occurrence` | Normalized prominence (0–1) from chunk coverage |

Importer today (before this work) looped all collections and created `partition_id_index` on `["partition_id"]` only when `partition_id` was set on the import job. `create_persistent_index` did not support `storedValues`.

---

## 3. Solution brainstorm

We evaluated eight approaches (including baseline).

| ID | Idea | Ticket fit |
|----|------|------------|
| **baseline** | Keep `partition_id_index` only | Insufficient |
| **A1** | Add composite; keep old Communities `partition_id_index` | Partial — redundant index |
| **A2** | Add composite + drop old Communities `partition_id_index` | Strong — correct behavior |
| **B** | Data-driven specs encoding A2 | **Best ship form** |
| **C** | Composite **without** `storedValues` | Incomplete vs ticket |
| **D** | A2 + migration packaging for existing DBs | Companion, not replacement |
| **E** | Retriever cache / rewrite / skinny side collection | Out of importer scope |
| **F** | Composite on **all** collections | Incorrect (`level`/`occurrence` not universal) |

### Design principles used

- Match filters with composite field order: `partition_id` then `level`.
- Include `storedValues: ["occurrence"]` for covering-style returns.
- Specialize Communities; do not break other collections’ partition indexes.
- Prefer idempotent create/drop with `inBackground: true`.
- Prefer ordered field matching over `set(fields)` for composite equality.

---

## 4. Decision

**Accepted: Solution B (= A2 behavior).**

Documented in [`community_schema_index_decision.md`](community_schema_index_decision.md).

### What ships

| Scope | Behavior |
|-------|----------|
| Communities | Create `partition_id_level_index` on `["partition_id", "level"]` with `storedValues: ["occurrence"]` |
| Communities | Drop / stop creating redundant `partition_id_index` |
| Other collections | Keep `partition_id_index` |
| Structure | Declarative specs (`IndexStrategy.B` as `PRODUCTION_STRATEGY`) |

### Why B/A2 wins for this ticket

1. Matches the proposed `ensureIndex` exactly (fields, stored values, name, background).
2. `storedValues` is required for the RETURN clause’s latency story.
3. Composite order matches `IN` + `<=` filters.
4. No redundant Communities index (unlike A1).
5. Scoped only where `level`/`occurrence` exist (unlike F).
6. B packages A2 cleanly for future index specs without changing the effective plan.

### Rejected options (short)

- **A1** — extra write/disk for unused Communities `partition_id_index`.
- **C** — misses ticket’s `storedValues` and covering reads.
- **E** — retriever work; does not fulfill “change importer index process”.
- **F** — wrong schema assumptions on non-Communities collections.
- **D** — keep as optional migration script for live DBs that won’t re-init.

---

## 5. Implementation

### 5.1 Core modules / changes

| Piece | Location |
|-------|----------|
| Strategy plans A–F + evaluation | `graphrag/importer/partition_index_strategies.py` |
| In-memory scale cost model | `graphrag/importer/community_schema_scale_bench.py` |
| Apply plan on init | `ImportGraphToADB._ensure_partition_indexes()` |
| `stored_values` support + ordered field match | `ImportGraphToADB.create_persistent_index()` |
| Index name constants | `CollectionIndexNames` in `graphrag/naming.py` |
| Migration helper (Option D) | `scripts/migrate_communities_partition_level_index.py` |
| Strategy reporter | `scripts/compare_partition_index_strategies.py` |
| Semi-live harness | `scripts/semi_live_community_schema_bench.py` |

### 5.2 Production index payload

```json
{
  "type": "persistent",
  "fields": ["partition_id", "level"],
  "name": "partition_id_level_index",
  "inBackground": true,
  "storedValues": ["occurrence"]
}
```

### 5.3 User-facing note

Communities section in `docs/user_facing_documentation.md` documents the new composite index purpose.

---

## 6. Testing & evidence

### 6.1 Strategy rubric (7 checks)

Checks: composite fields, stored occurrence, index name, others keep partition index, no redundant Communities partition index, no level composite on non-Communities, implementable in importer.

| Strategy | Score | Result |
|----------|-------|--------|
| baseline | 3/7 | FAIL |
| A1 | 6/7 | FAIL |
| **A2 / B / D** | **7/7** | **PASS** |
| C | 6/7 | FAIL |
| E | 1/7 | FAIL |
| F | 5/7 | FAIL |

Unit suite: `tests/unit/test_partition_index_strategies.py` — **17 passed**.

Full table: [`community_schema_index_results.md`](community_schema_index_results.md)

### 6.2 Scalable synthetic benchmark

Access patterns modeled: baseline, C (composite no stored), A2/B/D (covering). Scales **1k → 250k**.

Highlights at **250k**:

| Metric | baseline | C | A2/B/D |
|--------|---------:|--:|-------:|
| median_ms | 10.264 | 7.100 | **3.893** |
| full_doc_fetches | 37,295 | 18,604 | **0** |
| approx_bytes | ~153 MB | ~76 MB | **~1.2 MB (~0.78%)** |

Covering path keeps **0** full fetches; bytes stay ~**1%** of baseline across scales.

Details: [`scale_bench/community_schema_scale_results.md`](scale_bench/community_schema_scale_results.md)  
Unit: `tests/unit/test_community_schema_scale.py`

### 6.3 Semi-live ArangoDB 3.12.4

Local single-node ArangoDB (auth disabled). Same AQL; only indexes change between phases. Collection name used in harness: `nvbugs_b1_Communities` (ticket example).

| Docs | baseline median | B median | Speedup | EXPLAIN |
|------|----------------:|---------:|--------:|---------|
| 50k | 18.63 ms | 13.86 ms | **1.34×** | `partition_id_level_index` |
| 150k | 55.40 ms | 36.92 ms | **1.50×** | `partition_id_level_index` |

Confirmed after B:

- `fields: ["partition_id", "level"]`
- `storedValues: ["occurrence"]`
- `partition_id_index` removed
- identical result counts

Reports: [`semi_live/`](semi_live/)  
Pytest: `tests/unit/test_semi_live_community_schema.py` (skips if ArangoDB unreachable)

### 6.4 Combined test snapshot

| Suite | Result |
|-------|--------|
| Strategy unit tests | 17 passed |
| Scale unit tests | 7 passed (incl. large 50k/100k cases) |
| Semi-live pytest | 1 passed (when ADB up) |
| Semi-live harness 50k / 150k | Completed; reports written |

---

## 7. How to reproduce

### Strategy comparison

```bash
PYTHONPATH=. python scripts/compare_partition_index_strategies.py
PYTHONPATH=. python -m pytest tests/unit/test_partition_index_strategies.py --noconftest -q
```

### In-memory scale bench

```bash
PYTHONPATH=. python scripts/run_community_schema_scale_bench.py \
  --scales 1000 5000 10000 50000 100000 250000 --rounds 7
```

### Semi-live (ArangoDB required)

```bash
# Start ArangoDB on :8529 with authentication disabled, then:
PYTHONPATH=. python scripts/semi_live_community_schema_bench.py \
  --n-docs 50000 --rounds 7 \
  --out docs/semi_live/community_schema_semi_live.md
```

### Existing DB migration (Option D helper)

```bash
python scripts/migrate_communities_partition_level_index.py nvbugs_b1_Communities
# paste printed JS into arangosh
```

---

## 8. Timeline of work (this engagement)

1. **Understood the problem** — query shape, fat docs, importer ownership, existing `partition_id_index`.
2. **Brainstormed A–F** — trade-offs for composite, storedValues, scope, migration, retriever-side ideas.
3. **Implemented comparable strategies** — pure plans + production wiring to B.
4. **Unit + scale tests** — rubric scores and 1k–250k cost/time model.
5. **Chose B/A2** — decision record written into the repo.
6. **Semi-live ArangoDB validation** — real EXPLAIN + latency before/after.
7. **This full report + PowerPoint** — consolidated artifact for stakeholders.

---

## 9. Follow-ups

Not required to close the importer ticket, but recommended:

1. Integration test asserting `partition_id_level_index` exists on Communities after a full import.
2. Run Option D migration on production/staging DBs that will not re-run importer init.
3. Retriever-side latency capture (p50/p95) against real workloads / `EXPLAIN` in cluster.
4. Optional: measure write amplification of the new index under heavy import load.

---

## 10. Artifact index

| Artifact | Path |
|----------|------|
| **This report** | `docs/community_schema_optimization_full_report.md` |
| **PowerPoint** | `docs/community_schema_optimization_deck.pptx` |
| Decision record | `docs/community_schema_index_decision.md` |
| Strategy comparison | `docs/community_schema_index_results.md` |
| Scale bench | `docs/scale_bench/` |
| Semi-live reports | `docs/semi_live/` |
| User guide note | `docs/user_facing_documentation.md` (Communities indexes) |
| Changelog | `CHANGELOG.md` (Unreleased) |
| PR | https://github.com/arangoml/graphrag_importer/pull/227 |

---

## 11. Bottom line

**Ship solution B (= A2):** Communities get `partition_id_level_index` on `(partition_id, level)` with `storedValues: ["occurrence"]`, created by the importer at init; drop the redundant single-field Communities partition index. Evidence from design scoring, scalable modeling, and semi-live ArangoDB all support this as the ticket-aligned, measurable fix for Community Schema query latency.
