# Problem

## Summary

The Community Schema AQL query contributes meaningfully to **retriever latency**. Today the importer only creates a single-field persistent index on `partition_id`. That is not enough for a query that also filters on `level` and returns `occurrence` without needing the rest of the (often large) community document.

## Hot query (retriever)

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

## Why it is expensive

Community documents are fat: `report_string`, `report_json`, embeddings, `sub_communities`, etc.

With only `partition_id_index`:

1. ArangoDB can narrow by partition.
2. It still must evaluate `level <= @level` on candidates.
3. It typically loads full documents to read `occurrence`.

Ideal path: **index range scan** on `(partition_id, level)` plus **`occurrence` available from the index** (`storedValues`), so the engine does not fetch full docs.

## Current importer behavior

In `graphrag/importer/import_graph_to_adb.py` → `initialize()`:

- If `partition_id` is set, for every existing collection:
  - create `partition_id_index` on `["partition_id"]`

`create_persistent_index()` supports fields / name / unique / sparse / `inBackground`, but **not** `storedValues`.

## Relevant Communities fields

| Field | Meaning |
|-------|---------|
| `partition_id` | Logical partition (AutoGraph RAG partition / standalone batch) |
| `level` | Hierarchical community level from Leiden clustering |
| `occurrence` | Normalized prominence score (0–1) from chunk coverage |

## Ownership split

| Concern | Owner |
|---------|-------|
| Latency symptom / AQL | Retriever (outside this importer) |
| Index creation at graph init | **graphrag_importer** (this work) |

## Proposed index

```js
db._collection("nvbugs_b1_Communities").ensureIndex({
  type: "persistent",
  fields: ["partition_id", "level"],
  storedValues: ["occurrence"],
  name: "partition_id_level_index",
  inBackground: true
});
```

## Why a composite index helps

- Field order `partition_id` then `level` matches `IN` + `<=` filters.
- `storedValues: ["occurrence"]` keeps payload in the index for covering-style returns.
- Leading `partition_id` still helps partition-only filters on Communities.
