---
name: kb-check
description: Run a quality spot-check on the workspace knowledge base
---

# Check knowledge base quality

Run a quality check on the existing knowledge base.

1. Use the knowledge base root at `knowledge-base/` in this workspace unless the user provides another path.
2. Invoke `kb-critic` with that root.
3. Summarize the quality report (PASS / WARN / FAIL) and list concrete issues.
