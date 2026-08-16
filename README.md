# KB Genie — Agentic Worklow Plugin

Transform raw technical documents into an agent-optimized hierarchical knowledge base with semantic chunks, structured summaries, a living concept wiki, and quality-gated indexing.

## What It Does

1. **Converts raw documents to clean Markdown** — normalizes heading hierarchy, removes headers/footers/page numbers/OCR noise, preserves code blocks and tables
2. **Produces structured document summaries** — extracts key claims, methods, results, limitations, relevance assessment, and search tags into YAML frontmatter
3. **Splits documents into semantic chunks** — divides content on heading boundaries (not arbitrary token limits), enriches each chunk with summary, keywords, entities, semantic key, and potential questions
4. **Maintains a living concept wiki** — extracts concepts from all documents, creates new wiki entries and updates existing ones as new documents are ingested
5. **Keeps an authoritative master index** — single YAML catalog listing every processed document with metadata, file paths, chunk counts, and concept links
6. **Builds a knowledge graph** (optional) — extracts entities and relations from chunks to produce a structured graph in JSON format
7. **Runs quality spot-checks** — samples 20% of documents (minimum 3), validates all metadata fields, checks for near-duplicate chunks, verifies index completeness

## Agents

| Agent | Model | Role |
|-------|-------|------|
| `@kb.orchestrator` | sonnet | Plans ingestion runs, spawns workers, monitors progress, maintains index.yaml, produces status reports |
| `@kb.ingestion` | sonnet | Detects new/changed files in raw/, converts to clean Markdown, extracts bibliographic metadata |
| `@kb.summarizer` | sonnet | Produces structured document-level summaries with YAML frontmatter |
| `@kb.chunker` | sonnet | Splits Markdown into semantic chunks with rich metadata enrichment |
| `@kb.concept-distiller` | sonnet | Maintains living wiki under concepts/ — creates and updates concept pages |
| `@kb.indexer` | fast | Keeps index.yaml authoritative — scans outputs, updates catalog |
| `@kb.graph-builder` | sonnet | Extracts entities and relations from chunks to produce knowledge graph JSON |
| `@kb.critic` | sonnet | Quality spot-checks of summaries, chunks, concept pages, and index |

## Quick Start

### Install

```bash
npx kb-genie
```

Or for a specific target:

```bash
npx kb-genie install
```

### Ingest Documents

1. Create a knowledge base directory and place your documents in `raw/`:

```
knowledge-base/
└── raw/
    ├── whitepaper-2026.pdf
    ├── spec-api-v2.docx
    └── notes-meeting-2026.md
```

2. Open Cursor and invoke the orchestrator:

```
@kb.orchestrator

Knowledge base root: /path/to/knowledge-base/
Ingest all new files in raw/
```

The orchestrator will run all 7 specialist agents automatically, validate outputs at each phase, and produce a final status report.

### Individual Agent Invocation

You do not have to run the full pipeline every time:

```
@kb.chunker

Knowledge base root: /path/to/knowledge-base/
Documents: whitepaper-2026, spec-api-v2
```

```
@kb.critic

Knowledge base root: /path/to/knowledge-base/
```

```
@kb.indexer

Knowledge base root: /path/to/knowledge-base/
```

## Knowledge Base Folder Structure

```
knowledge-base/
├── raw/                          # IMMUTABLE originals (never modified by agents)
├── markdown/                     # Clean full-document Markdown
├── summaries/                    # Document-level summaries (YAML frontmatter)
├── chunks/                       # Semantic chunks (one .md per chunk)
├── concepts/                     # Living wiki (one .md per concept)
├── graphs/                       # Knowledge graph JSON (optional)
├── index.yaml                    # Master catalog
├── logs/
│   └── ingestion-runs/
│       ├── run-YYYYMMDD-NNN.log
│       └── run-YYYYMMDD-NNN-quality.md
└── tasks/
    ├── pending/
    ├── in-progress/
    └── completed/
```

## CLI Reference

```bash
npx kb-genie              # Show usage
npx kb-genie install      # Copy knowledge-base template to current directory
npx kb-genie info         # Show agent inventory
```

## Pipeline

```
Input: knowledge base root directory + (optional) file list
         ↓
[Stage 1]  kb.orchestrator → run log + task queue
         ↓
[Stage 2]  kb.ingestion    → markdown/<doc_id>.md + summaries/<doc_id>.meta.yaml
         ↓
[Stage 3]  kb.summarizer   → summaries/<doc_id>.md
         ↓
[Stage 4]  kb.chunker      → chunks/<chunk_id>.md
         ↓
[Stage 5]  kb.concept-distiller → concepts/<concept-slug>.md
         ↓
[Stage 6]  kb.indexer      → index.yaml
         ↓
[Stage 7]  kb.graph-builder  → graphs/knowledge-graph.json (optional, parallel)
[Stage 7]  kb.critic         → run log quality report (parallel)
         ↓
   Final Status Report → User
```

## Dependencies

```bash
# Required CLI tools for document conversion:

# Pandoc — universal document converter (macOS: brew install pandoc, Linux: apt-get install pandoc)
# pdftotext — PDF text extraction (macOS: brew install poppler, Linux: apt-get install poppler-utils)

# Optional: Python for embedding-based near-duplicate detection
pip install sentence-transformers numpy
```

## Quality Gates

| Gate | Requirement |
|------|-------------|
| Every chunk | non-empty summary |
| Every chunk | non-empty semantic_key |
| Every chunk | at least one potential_question |
| Every concept page | cites at least one source chunk |
| Every concept page | non-empty Definition section |
| Every document summary | non-empty relevance_to_software |
| Near-duplicate chunks | cosine similarity > 0.95 → merge or flag |
| index.yaml | lists every processed document |

## License

MIT
