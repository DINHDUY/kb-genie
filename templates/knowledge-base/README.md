# Knowledge Base

Place raw documents (PDF, DOCX, HTML, Markdown) in the `raw/` directory.

Agents will never modify files in `raw/`. All processed output goes into the directories below.

## Directories

- `raw/` — Original documents (immutable)
- `markdown/` — Clean, normalized Markdown output
- `summaries/` — Document-level summaries with YAML frontmatter
- `chunks/` — Semantic chunks with rich metadata
- `concepts/` — Living concept wiki
- `graphs/` — Knowledge graph JSON (optional)
- `logs/ingestion-runs/` — Run logs and quality reports
- `tasks/` — Task queues for pipeline coordination

## Getting Started

1. Drop your documents into `raw/`
2. Open Cursor and run:
   ```
   @kb.orchestrator

   Knowledge base root: /path/to/this/directory/
   Ingest all new files in raw/
   ```
