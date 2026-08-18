---
name: kb-genie
description: >-
  Answer Genie-prefixed chat intents from the workspace knowledge base only,
  using the kb-rag CLI. Use when the user types "Genie,", "Genie!", or "Genie:"
  followed by an intent (for example "Genie, what is X?"). Do not search the
  web or other folders.
---

# KB Genie (chat)

Apply this skill when the user message starts with `Genie,`, `Genie!`, or `Genie:` (any capitalization of "Genie"). The rest of the message is the `<intent>`.

## Hard rules

- Only return data from the knowledge-base using the available tools.
- Do not hallucinate or search the web, or any other folder.
- If the answer for the `<intent>` cannot be found just say so.
- Always cite the sources, unless the `<intent>` states otherwise.
- Read-only: do not modify the knowledge base.

## Knowledge-base root

Default `--kb-root` is `./knowledge-base` in the current project/workspace. Use a user-supplied path only if they override it. `KB_ROOT` is an allowed fallback if `./knowledge-base` is missing.

Require `index.yaml` and `graphs/knowledge-graph.json` (fallback: `graph/knowledge-graph.json`). If either is missing, say so and stop. Do not scan `chunks/` or other directories.

## Tools (kb-rag CLI)

Use only `kb-rag` from `tools/kb-rag` (`tools/kb-rag/src/kb_rag/cli.py`). If the command is missing:

```bash
pip install -e ./tools/kb-rag
```

Default: `--no-rerank`. Pass `--format json`.

1. Start with retrieve for the `<intent>`:

```bash
kb-rag --kb-root ./knowledge-base retrieve "<intent>" --top-k 8
```

2. Follow up only with these commands when the pack is incomplete:

```bash
kb-rag --kb-root ./knowledge-base search "<intent>"
kb-rag --kb-root ./knowledge-base get-doc DOC_ID
kb-rag --kb-root ./knowledge-base get-chunk CHUNK_ID
kb-rag --kb-root ./knowledge-base get-concept CONCEPT_ID
kb-rag --kb-root ./knowledge-base neighbors ENTITY_ID --hops 1
kb-rag --kb-root ./knowledge-base list-docs
```

Do not glob, grep, or read files under the knowledge base except through these commands.

## Answer

- Answer only from CLI output (chunk bodies, concepts, citations).
- If hits are empty or none support the `<intent>`, say the knowledge base does not contain an answer.
- Cite `chunk_id` (and `doc_id` / path from `citations`) for every claim, unless the `<intent>` says not to cite.