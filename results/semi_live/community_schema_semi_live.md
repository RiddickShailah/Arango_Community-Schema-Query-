# Semi-live Community Schema benchmark (solution B/A2)

Generated: 2026-07-14 17:54 UTC

## Environment

- ArangoDB: `3.12.4` at `http://127.0.0.1:8529`
- Database / collection: `community_schema_semi_live` / `nvbugs_b1_Communities`
- Docs: **50000**, partitions: 20, query partitions: 3, level ≤ 2
- Rounds: 7
- Solution under test: **B (= A2)** via `build_index_plan(IndexStrategy.B, …)`

## Query

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

## Results

| Phase | result_count | median_ms | p95_ms | mean_ms | used_indexes |
|-------|-------------:|----------:|-------:|--------:|--------------|
| baseline (partition_id_index) | 3811 | 18.627 | 19.804 | 18.697 | partition_id_index |
| solution B (partition_id_level_index) | 3811 | 13.862 | 14.397 | 13.900 | partition_id_level_index |

**Speedup (median):** 1.34x faster with solution B

### Baseline indexes

```json
[
  {
    "name": "partition_id_index",
    "fields": [
      "partition_id"
    ],
    "storedValues": null,
    "id": "208"
  }
]
```

### Solution B indexes

```json
[
  {
    "name": "partition_id_level_index",
    "fields": [
      "partition_id",
      "level"
    ],
    "storedValues": [
      "occurrence"
    ],
    "id": "262"
  }
]
```

### Solution apply log

- plan strategy=B ops=2
- dropped partition_id_index
- created partition_id_level_index payload={'type': 'persistent', 'fields': ['partition_id', 'level'], 'name': 'partition_id_level_index', 'inBackground': True, 'storedValues': ['occurrence']}

### Explain excerpts

<details><summary>Baseline explain (plan nodes types / indexes)</summary>

```json
{
  "used_indexes": [
    "partition_id_index"
  ],
  "nodes": [
    {
      "type": "SingletonNode",
      "id": 1,
      "indexes": null,
      "estimatedCost": 1,
      "estimatedNrItems": 1
    },
    {
      "type": "IndexNode",
      "id": 9,
      "indexes": [
        {
          "id": "208",
          "type": "persistent",
          "name": "partition_id_index",
          "fields": [
            "partition_id"
          ],
          "selectivityEstimate": 0.0004,
          "unique": false,
          "sparse": false,
          "deduplicate": true,
          "estimates": true,
          "cacheEnabled": false
        }
      ],
      "estimatedCost": 352.524101186092,
      "estimatedNrItems": 5000
    },
    {
      "type": "CalculationNode",
      "id": 7,
      "indexes": null,
      "estimatedCost": 5352.524101186092,
      "estimatedNrItems": 5000
    },
    {
      "type": "ReturnNode",
      "id": 8,
      "indexes": null,
      "estimatedCost": 10352.524101186093,
      "estimatedNrItems": 5000
    }
  ],
  "stats": {
    "rulesExecuted": 58,
    "rulesSkipped": 0,
    "plansCreated": 1,
    "rules": {},
    "peakMemoryUsage": 0,
    "executionTime": 0.00033768900902941823
  }
}
```

</details>

<details><summary>Solution B explain (plan nodes types / indexes)</summary>

```json
{
  "used_indexes": [
    "partition_id_level_index"
  ],
  "nodes": [
    {
      "type": "SingletonNode",
      "id": 1,
      "indexes": null,
      "estimatedCost": 1,
      "estimatedNrItems": 1
    },
    {
      "type": "IndexNode",
      "id": 9,
      "indexes": [
        {
          "id": "262",
          "type": "persistent",
          "name": "partition_id_level_index",
          "fields": [
            "partition_id",
            "level"
          ],
          "selectivityEstimate": 0.0024,
          "unique": false,
          "sparse": false,
          "storedValues": [
            "occurrence"
          ],
          "deduplicate": true,
          "estimates": true,
          "cacheEnabled": false
        }
      ],
      "estimatedCost": 157.17928094887364,
      "estimatedNrItems": 2500
    },
    {
      "type": "MaterializeNode",
      "id": 10,
      "indexes": null,
      "estimatedCost": 2657.179280948874,
      "estimatedNrItems": 2500
    },
    {
      "type": "CalculationNode",
      "id": 7,
      "indexes": null,
      "estimatedCost": 5157.179280948874,
      "estimatedNrItems": 2500
    },
    {
      "type": "ReturnNode",
      "id": 8,
      "indexes": null,
      "estimatedCost": 7657.179280948874,
      "estimatedNrItems": 2500
    }
  ],
  "stats": {
    "rulesExecuted": 58,
    "rulesSkipped": 0,
    "plansCreated": 1,
    "rules": {},
    "peakMemoryUsage": 0,
    "executionTime": 0.0002045540022663772
  }
}
```

</details>

## Behavior notes

- Same AQL and bind vars in both phases; only indexes change.
- Result counts must match (correctness).
- Expect EXPLAIN to prefer `partition_id_level_index` after solution B.
- Absolute ms depend on host; relative improvement and plan shape are the signal.
