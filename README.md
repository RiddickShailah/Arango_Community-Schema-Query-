# Arango Community Schema Query

Working notes for optimizing the **Community Schema** retriever query via a composite persistent index created in **graphrag_importer**.

## Goal

Reduce retriever latency for:

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

by ensuring the importer creates:

```js
ensureIndex({
  type: "persistent",
  fields: ["partition_id", "level"],
  storedValues: ["occurrence"],
  name: "partition_id_level_index",
  inBackground: true
})
```

## Related repos

| Repo | Role |
|------|------|
| [arangoml/graphrag_importer](https://github.com/arangoml/graphrag_importer) | Where indexes are created at import time (implementation target) |
| Retriever service (separate) | Owns the AQL query / latency symptom |

## Docs

| Doc | What it covers |
|-----|----------------|
| [docs/01-problem.md](docs/01-problem.md) | Problem, current behavior, why it is slow |
| [docs/02-solutions.md](docs/02-solutions.md) | Brainstormed options and trade-offs |
| [docs/03-recommendation.md](docs/03-recommendation.md) | Preferred approach and implementation checklist |
| [docs/04-code-touchpoints.md](docs/04-code-touchpoints.md) | Exact places in graphrag_importer to change |
| [WORKLOG.md](WORKLOG.md) | Chronological progress |

## Status

- [x] Understand the problem end-to-end
- [x] Brainstorm solutions
- [x] Choose final approach and implement in graphrag_importer (B=A2)
- [x] Tests (unit strategy suite 17 passed; integration index assertion still follow-up)
- [x] Existing-DB migration script (Option D helper)
- [ ] Verify retriever latency improvement


## Syncing this tracker

Cloud agents may not have write access to this personal GitHub repo. Local commit is already prepared.

```bash
# From a machine that can push to RiddickShailah/Arango_Community-Schema-Query-
git clone https://github.com/RiddickShailah/Arango_Community-Schema-Query-.git
# OR if using the prepared clone / export:
# unzip the artifact, then:
cd Arango_Community-Schema-Query-
git push -u origin main
```

Alternatively, add a collaborator/bot with write access, then re-run push from the cloud environment.

## Layout

```text
.
├── README.md                 # map + status
├── WORKLOG.md                # chronological progress
└── docs/
    ├── 01-problem.md
    ├── 02-solutions.md
    ├── 03-recommendation.md
    └── 04-code-touchpoints.md
```
