# KB Genie

Cursor plugin that turns raw technical documents into an agent-optimized knowledge base: clean Markdown, structured summaries, semantic chunks, a living concept wiki, and a quality-gated index.

Install this plugin from the parent repository via Cursor **Dashboard → Plugins → Team Marketplaces → Import from Repo**. For local testing, copy this directory to `~/.cursor/plugins/local/kb-genie` (a real directory, not an external symlink).

## Components

| Type | Names |
|------|--------|
| Agents | `kb-orchestrator`, `kb-ingestion`, `kb-summarizer`, `kb-chunker`, `kb-concept-distiller`, `kb-indexer`, `kb-graph-builder`, `kb-critic` |
| Skills | `kb-genie` (Genie-prefixed chat), `kb-ingest`, `kb-check`, `kb-index-rebuild` |
| Commands | `/kb-ingest`, `/kb-check`, `/kb-index-rebuild`, `/kb-retrieve` |
| Rules | `knowledge-base.mdc` |

For Genie chat and `/kb-retrieve`:

```bash
pip install -e skills/kb-genie/tools/kb-rag
```

Run that from this plugin directory, or from the repo root:

```bash
pip install -e plugins/kb-genie/skills/kb-genie/tools/kb-rag
```
