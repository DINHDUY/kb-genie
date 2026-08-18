# Knowledge-base RAG CLI for agents

Build a retrieve-only RAG toolkit in this repo. The calling Cursor agent does generation; the CLI returns ranked, cited context. The example knowledge base is `C:\work\panagoraeqds\eqds\quanthub-kb\knowledge-base`, but `--kb-root` works for any kb-genie tree.

Canonical graph path is **`graphs/knowledge-graph.json`** (existing kb-genie convention). Accept `graph/` only as a fallback.

## Retrieval contract

Every command that searches must load these first and fail fast if either is missing:

- `index.yaml` — document catalog (`doc_id`, `title`, `concepts`, `chunk_files`, `status`)
- `graphs/knowledge-graph.json` — `entities[].id/label/type/source_chunks` and `relations[].from/to/type/source_chunk`

```mermaid
flowchart TD
  query[Query] --> catalog[Load index.yaml]
  query --> graph[Load knowledge-graph.json]
  catalog --> docHits[Lexical rank documents]
  graph --> entityHits[Lexical rank entities]
  entityHits --> expand[1-hop neighbors]
  docHits --> candidates[Candidate chunk ids]
  expand --> candidates
  candidates --> chunks[Load chunk frontmatter]
  chunks --> lexical[Lexical score chunks]
  lexical --> rerank[Optional embedding rerank]
  rerank --> pack[JSON context pack]
```

Candidate chunks come only from catalog `chunk_files` of top documents plus graph `source_chunks` of matched/expanded entities. Do not scan the whole `chunks/` tree as the first hop.

Scoring (v1, no extra ML deps):

- Tokenize query (lowercase, alphanumerics, keep short tokens like `qaid`)
- Weighted field match: `semantic_key` > `title` > `keywords` / `potential_questions` > `entities` / catalog `concepts` > `summary` > body
- Exact phrase and kebab-id bonuses (`qa-id` ↔ `qaid`)
- Optional second pass: `sentence-transformers` cosine rerank of the top lexical hits only (no persistent embedding index)

Skip documents with `status` other than `processed`.

## CLI as agent tools

Installable as `kb-rag` (`python -m kb_rag`). JSON on stdout by default; errors as JSON on stderr with non-zero exit.

```text
kb-rag --kb-root PATH search "what is qaid"
kb-rag --kb-root PATH retrieve "what is qaid" --top-k 8
kb-rag --kb-root PATH get-doc usrdata-universe-notes
kb-rag --kb-root PATH get-chunk usrdata-universe-notes-chunk-015
kb-rag --kb-root PATH get-concept qaid
kb-rag --kb-root PATH neighbors qaid --hops 1
kb-rag --kb-root PATH list-docs
```

Global flags: `--kb-root` (or `KB_ROOT`), `--format json|text`, `--top-k`, `--rerank` / `--no-rerank`.

Tool roles:

- **search** — ranked mix of docs, entities, concepts, chunks (navigation)
- **retrieve** — RAG pack: top chunks (frontmatter + body), related concept pages, graph hops, citations (`doc_id`, `chunk_id`, path)
- **get-*** / **neighbors** / **list-docs** — exact lookups after search

No LLM calls in this package.

## Python layout (SOLID, one job per module)

New package under `tools/kb-rag/`, separate from the Node plugin CLI:

```text
tools/kb-rag/
  pyproject.toml
  src/kb_rag/
    __init__.py
    __main__.py
    cli.py              # argparse only; no retrieval logic
    models.py           # dataclasses: Document, Chunk, Entity, Hit, RetrievalPack
    paths.py            # KnowledgeBaseRoot: resolve index + graph paths
    catalog.py          # load/query index.yaml
    graph.py            # load/query knowledge-graph.json
    store.py            # read summaries/chunks/concepts (YAML frontmatter)
    scoring/
      tokenize.py
      lexical.py        # field-weighted scorer
      embeddings.py     # optional rerank; import-guarded
    retrieve.py         # orchestrates catalog → graph → chunks
  tests/
```

Install from the repo root with `pip install -e ./tools/kb-rag` (or `pip install -e "./tools/kb-rag[embeddings]"`).

Rules:

- CLI depends on `retrieve` / `store`; those do not import `cli`
- Scorers implement a small `Ranker` protocol so embeddings stay optional
- Parse frontmatter with PyYAML (no `python-frontmatter` unless needed)
- Core deps: `PyYAML`. Extra: `kb-rag[embeddings]` → `sentence-transformers`, `numpy`
- Python 3.11+, `ruff` + `pytest`

`tools/kb-rag/pyproject.toml` console script: `kb-rag = "kb_rag.cli:main"`.

## Cursor plugin wiring

Add to the installable plugin only (`plugins/kb-genie/`), which `scripts/validate-plugin.mjs` already scans:

- Skill `plugins/kb-genie/skills/kb-retrieve/SKILL.md`: when the user asks a question against a knowledge base, run `kb-rag` instead of grepping `chunks/` first; prefer `retrieve`, then `get-chunk` / `get-concept` / `neighbors`; cite `chunk_id`s
- Command `plugins/kb-genie/commands/kb-retrieve.md`: `/kb-retrieve` with `--kb-root` (default workspace `knowledge-base/`)
- Update `plugins/kb-genie/README.md`, root `README.md`, and `plugins/kb-genie/rules/knowledge-base.mdc` with the catalog-first rule and CLI
- After merge, copy the new skill/command into `%USERPROFILE%\.cursor\plugins\local\kb-genie\` so local Cursor picks it up

No new agent. Skills + commands + CLI are enough.

## Tests

Use a tiny fixture tree (2 docs, ~4 chunks, 3 entities, 2 relations, 1 concept):

- Missing index or graph → non-zero exit
- Query matching a catalog concept returns that doc’s chunks
- Graph neighbor expansion includes related `source_chunks`
- `get-chunk` / `get-concept` round-trip
- `--rerank` without extras installed degrades cleanly to lexical

Smoke against the real quanthub-kb path in docs only, not as a required unit test.

## Implementation checklist

- Add `tools/kb-rag` package: `pyproject.toml`, models, paths, catalog, graph, store
- Implement lexical Retriever + argparse CLI (`search`, `retrieve`, `get-*`, `neighbors`, `list-docs`) with JSON output
- Add optional sentence-transformers rerank extra that reranks lexical top hits only
- Add pytest fixture knowledge base covering catalog-first, graph expansion, and missing-artifact failures
- Add kb-retrieve skill + command, update README/rules, sync to local plugin dir

## Out of scope

- Ingestion, chunking, graph rebuild (existing kb-genie agents)
- Persistent vector DB or embedding cache
- Answer generation / LLM API calls
- Changing the Node `npx kb-genie` installer beyond README mention
