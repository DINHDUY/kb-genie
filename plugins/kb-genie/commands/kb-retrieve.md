---
name: kb-retrieve
description: Retrieve ranked, cited context from the workspace knowledge base via kb-rag
---

# Retrieve knowledge-base context

Run retrieve-only RAG against a kb-genie tree. You generate the answer; `kb-rag` returns ranked context.

1. Use `--kb-root` if the user provided a path. Otherwise default to `knowledge-base/` in this workspace (or `KB_ROOT`).
2. Prefer:

```bash
kb-rag --kb-root knowledge-base retrieve "$ARGUMENTS" --top-k 8
```

3. Follow up with `get-chunk`, `get-concept`, or `neighbors` as needed. Cite `chunk_id`s.
4. Do not grep or glob `chunks/` first. If `index.yaml` or `graphs/knowledge-graph.json` is missing, stop and tell the user to ingest / build the graph.
