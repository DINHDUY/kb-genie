---
name: kb-check
description: Run a quality spot-check on an existing knowledge base. Use when the user wants to validate summaries, chunks, concept pages, or index.yaml after an ingestion run.
---

# Check knowledge base quality

## When to use

- After an ingestion run
- When the user asks if the knowledge base is complete or consistent
- When near-duplicate chunks or missing index entries are suspected

## Instructions

1. Confirm the knowledge base root. Prefer `knowledge-base/` in the workspace.
2. Verify `summaries/`, `chunks/`, and `index.yaml` exist. If they do not, tell the user to run `/kb-ingest` first.
3. Invoke the `kb-critic` agent with the knowledge base root path.
4. Read the generated quality report under `logs/ingestion-runs/` and summarize PASS / WARN / FAIL with the concrete issues.
5. Do not rewrite documents unless the user asks to fix the reported issues.
