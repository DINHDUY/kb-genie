---
name: kb-ingest
description: Run the full knowledge base ingestion pipeline on the workspace knowledge-base directory
---

# Ingest documents

Run the knowledge base ingestion pipeline.

1. Use the knowledge base root at `knowledge-base/` in this workspace unless the user provides another path.
2. Place or confirm raw documents in `raw/`.
3. Invoke `kb-orchestrator` with that root and ingest all new or changed files in `raw/`.
4. Return the orchestrator status report, quality result, and paths to `index.yaml` and the run logs.
