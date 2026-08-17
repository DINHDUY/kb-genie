---
name: kb-index-rebuild
description: Rebuild the authoritative index.yaml from current knowledge base output directories. Use when the catalog is stale, missing entries, or out of sync with summaries and chunks.
---

# Rebuild knowledge base index

## When to use

- `index.yaml` is missing, corrupt, or incomplete
- New summaries or chunks exist that are not listed in the catalog
- The user asks to refresh or rebuild the index only

## Instructions

1. Confirm the knowledge base root. Prefer `knowledge-base/` in the workspace.
2. Scan `summaries/`, `markdown/`, `chunks/`, `concepts/`, and `raw/` so you can describe what the indexer should catalog.
3. Invoke the `kb-indexer` agent with the knowledge base root path.
4. After it finishes, confirm `index.yaml` lists every processed document and that file paths resolve.
5. Report entry counts for processed, pending, and archived documents.
