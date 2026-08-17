---
name: kb-ingest
description: Run a full knowledge base ingestion pipeline. Use when the user wants to convert raw documents in a knowledge-base raw/ directory into Markdown, summaries, chunks, concepts, and an index.
---

# Ingest knowledge base documents

## When to use

- New files were added to `knowledge-base/raw/`
- The user asks to ingest, process, or rebuild a knowledge base
- An interrupted ingestion run should be resumed

## Instructions

1. Confirm the knowledge base root. Prefer `knowledge-base/` in the workspace. If it is missing, tell the user to run `npx kb-genie init` or create the folder from the plugin template.
2. Confirm `raw/` contains documents (PDF, DOCX, HTML, or Markdown). Do not modify files in `raw/`.
3. Invoke the `kb-orchestrator` agent with the knowledge base root path and either a specific file list or "ingest all new files in raw/".
4. Let the orchestrator run specialists in order: `kb-ingestion` → `kb-summarizer` → `kb-chunker` → `kb-concept-distiller` → `kb-indexer`, then optional `kb-graph-builder` and `kb-critic`.
5. Report the final status, quality result, and paths to `index.yaml`, the run log, and the quality report.
