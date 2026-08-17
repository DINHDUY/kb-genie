---
name: kb-index-rebuild
description: Rebuild index.yaml from current knowledge base output directories
---

# Rebuild the index

Rebuild the authoritative knowledge base catalog.

1. Use the knowledge base root at `knowledge-base/` in this workspace unless the user provides another path.
2. Invoke `kb-indexer` with that root so it scans output directories and updates `index.yaml`.
3. Report how many processed, pending, and archived entries were written.
