# US DEV build request — Community Schema partition index

**Simple request:** Deploy / verify **graphrag_importer** commit below on **US DEV**, ensure Communities has `partition_id_level_index`, then time **two retriever questions** and fill the report table.

> This ticket does **not** change retriever code. Deploy the **importer**. Use the **retriever** only to ask questions and measure wall time.

---

## Gate status (ready)

| Gate | Status |
|------|--------|
| PR | [#228](https://github.com/arangoml/graphrag_importer/pull/228) — OPEN, MERGEABLE |
| Unit tests (`test-1`) | ✅ PASS |
| Integration (`cpu_only` + `cpu_and_gpu`) | ✅ PASS |
| Lint / pyinstaller / changelog | ✅ PASS |
| DEV image build + push | ✅ PASS (`image-commit-dev`) |
| DEV chart publish | ✅ PASS (`chart-commit-dev`) |
| DEV refresh Step Function | ✅ PASS (`refresh-dev-2`) |

**Commit:** `ae1883568d0ba427e44d461607eef8a07b41faf3`  
**Branch:** `cursor/community-schema-partition-index-ade5`  
**Image tag:** `v0.0.30-ae18835`  
**DEV image:**  
`889010145541.dkr.ecr.us-east-1.amazonaws.com/release/dev/graphrag-importer/service:v0.0.30-ae18835`

---

## What to deploy

Production behavior on this commit:

- Communities: `partition_id_level_index` on `(partition_id, level)` with `storedValues: ["occurrence"]`
- Other collections: still `partition_id_index`
- Existing graphs: run migration script (or re-import with `partition_id` set)

---

## US DEV steps

1. **Merge** PR #228 to `main` when approved (CI already green).
2. Confirm US DEV GenAI/platform is on importer image **`v0.0.30-ae18835`** (or the post-merge SHA tag if rebuilt from `main`).  
   - Note: CircleCI already published this PR SHA to the **dev** registry and ran `refresh-dev`.
3. On the US DEV Arango graph used for GraphRAG testing:
   - Prefer a graph with real `partition_id` values (like Pilot `test_deep_search`).
   - Migrate if the index is missing:

```bash
PYTHONPATH=. poetry run python scripts/migrate_communities_partition_level_index.py \
  --url "$US_DEV_ARANGO_URL" \
  --db "$US_DEV_DB" \
  --collection "${GENAI_PROJECT_NAME}_Communities"
```

4. Verify index:

```aql
FOR idx IN Indexes("YOUR_PROJECT_Communities")
  FILTER idx.name == "partition_id_level_index"
  RETURN { name: idx.name, fields: idx.fields, storedValues: idx.storedValues }
```

5. **Time the Community Schema AQL** (primary metric for this ticket):

```aql
FOR c IN @@communities_collection
  FILTER c.partition_id IN @partition_ids
  FILTER c.level <= @level
  RETURN { _key: c._key, level: c.level, occurrence: c.occurrence }
```

Record profile / driver wall ms + confirm EXPLAIN uses `partition_id_level_index`.

6. **Ask two retriever questions** on that same graph (global + local). Record **wall time only** (`time` / `WALL_TIME_SEC`).

---

## Timing report (fill for US DEV)

### A. Community Schema AQL (ticket focus)

| Env | Graph | Partition | Level | Rows | Wall / profile | EXPLAIN index | Notes |
|-----|-------|-----------|------:|-----:|---------------:|---------------|-------|
| Pilot (done) | `test_deep_search` / `_system` | `default_1_a` | ≤2 | 525 | **~3.384 ms** | `partition_id_level_index` | storedValues occurrence |
| US DEV | | | | | | | |

### B. Retriever E2E questions (product path)

| # | Question | Type | Env | Wall time | Notes |
|---|----------|------|-----|----------:|-------|
| 1 | What are the main themes or communities in this dataset? | global | Pilot (done) | **24.135 s** (`WALL`) / ~26.0 s `real` | 512 communities; LLM-bound |
| 2 | Tell me about ArangoSearch views and how they relate to analyzers and indexes. | local | Pilot (done) | **5.852 s** (`WALL`) / ~7.7 s `real` | 10 entities |
| 1 | *(same Q1)* | global | **US DEV** | | |
| 2 | *(same Q2)* | local | **US DEV** | | |

### C. How to report

Paste into the PR / ticket:

```text
US DEV timing report — importer v0.0.30-ae18835 (or merged SHA)

AQL Community Schema: ___ ms · rows ___ · EXPLAIN: partition_id_level_index? Y/N
Q1 global wall: ___ s
Q2 local wall: ___ s

Graph: ___ · DB: ___ · partition: ___ · level: ___
```

**Interpretation reminder:** AQL ms proves the index. E2E seconds are mostly LLM; report both separately.

---

## Pilot reference (already measured)

Full write-up: tracking repo `docs/08-pilot-retriever-findings.md`  
PR: https://github.com/arangoml/graphrag_importer/pull/228
