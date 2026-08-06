# Knowledge Engine Validation Console (Developer Only)

Engineering dashboard for Phase 13 Shadow Mode validation.

**Not** part of the React frontend. **No** production deployment.

## Purpose

Help engineers decide whether the Knowledge Intelligence Engine is ready to advance:

- Is it working correctly?
- Does it add structured intelligence beyond the legacy pipeline?
- Is it safe to move to the next milestone?
- What still needs improvement?

## Features

1. Knowledge Object Inspector (click any document row)
2. Capability comparison table (Legacy vs Knowledge Engine / Registry)
3. Confidence explanation (heuristic estimates clearly labeled)
4. Validation history across runs
5. Phase approval gate (13.1–13.7 approved · 13.8 active)
6. Per-document processing timeline
7. Expandable validation checklist details
8. Known issues + resolved issues history
9. Full Phase 13 roadmap status
10. **Knowledge Registry section (Phase 13.2)** — collections, taxonomy, aliases, versions, duplicates, health, coverage
11. **Relationship Explorer (Phase 13.3)** — edge stats, types, confidence distribution, top connected docs, evidence table
12. **Hybrid Knowledge Index (Phase 13.4)** — index summary, per-index stats, coverage, Index Explorer, Lookup Explorer, performance
13. **Intelligent Query Planner (Phase 13.5)** — planner summary, interactive plan viewer, diagnostics, metrics (no retrieval)
14. **Knowledge Execution Engine (Phase 13.6)** — plan execution summary, explorer, evidence inspector, provider metrics
15. **Knowledge Graph (Phase 13.7)** — graph summary, explorer, traversal, expansion viewer, diagnostics
16. **Worker Orchestration (Phase 13.8)** — worker registry, execution explorer/timeline, merger, diagnostics

## How to use

From `backend/`:

```bash
python -m scripts.run_knowledge_engine_validation
```

Then serve this folder:

```bash
cd knowledge_engine/validation
python -m http.server 8765
```

Open `http://localhost:8765/` in a browser.

> Do **not** open `index.html` via `file://` — browsers block `fetch()` of local JSON.

## Data files

| File | Role |
|------|------|
| `data/phase_13_1.json` | Current dashboard payload |
| `data/validation_history.json` | Append-only run history |
| `data/phase_13_1_report.md` | Markdown summary for PRs/reviews |

The console is JSON-driven. Future milestones can extend the same schema without React or backend API changes.
