# Interactive findings demo

Self-contained slideshow website with Chart.js graphs from our measured results.

## Open locally

```bash
# from repo root
open docs/interactive/index.html
# or
python3 -m http.server 8080 --directory docs/interactive
# then visit http://127.0.0.1:8080
```

## Controls

- **Next / Prev** buttons
- Keyboard: `→` `←` `Space` `Esc` `Home` `End`
- Slide dots in the footer

## What’s inside

| Slide | Content |
|-------|---------|
| 1 | Hero / ticket framing |
| 2 | Problem + AQL |
| 3 | Proposed ensureIndex |
| 4 | Strategies A–F rubric chart |
| 5 | Decision B (= A2) |
| 6 | Scale latency chart (1k–250k) |
| 7 | Full fetches / bytes chart |
| 8 | Semi-live ArangoDB before/after |
| 9 | Implementation code |
| 10 | Bottom line metrics |

## GitHub Pages (personal tracker)

On `RiddickShailah/Arango_Community-Schema-Query-`:

1. Copy `docs/interactive/` → repo root as `docs/` **or** keep under `website/` and set Pages to `/docs`
2. Settings → Pages → Deploy from branch `main` → folder `/docs` (if `index.html` is at `docs/index.html`)

Recommended layout for Pages:

```text
docs/index.html   ← this file renamed/copied
```

Then site URL:

`https://riddickshailah.github.io/Arango_Community-Schema-Query-/`
