"""Test helpers and tiny fixture KB writer for kb-rag.

Never globs or walks chunks/ to discover files (constitution BAN-01 / TEST-07).
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

DOC_NOTES = "usrdata-universe-notes"
DOC_BARRA = "barra-id-mapping"
DOC_SKIPPED = "draft-skipped-doc"

CHUNK_NOTES_1 = "usrdata-universe-notes-chunk-001"
CHUNK_NOTES_2 = "usrdata-universe-notes-chunk-002"
CHUNK_BARRA_1 = "barra-id-mapping-chunk-001"
CHUNK_BARRA_2 = "barra-id-mapping-chunk-002"
CHUNK_SKIPPED = "draft-skipped-doc-chunk-001"
CHUNK_DECOY = "decoy-not-in-catalog-chunk-999"

ENTITY_QAID = "qaid"
ENTITY_BARRA = "barra-id"
ENTITY_DS = "ds-regional-id"

CONCEPT_QAID = "qaid"
DECOY_TOKEN = "unicorn-decoy-token"
SKIPPED_TOKEN = "secret-draft-token"

PROCESSED_CHUNK_FILES = (
    f"{CHUNK_NOTES_1}.md",
    f"{CHUNK_NOTES_2}.md",
    f"{CHUNK_BARRA_1}.md",
    f"{CHUNK_BARRA_2}.md",
)


@dataclass(slots=True)
class FixtureKB:
    root: Path
    index_path: Path
    graph_path: Path


def _md(frontmatter: str, body: str) -> str:
    return f"---\n{frontmatter.strip()}\n---\n\n{body.strip()}\n"


def write_fixture_kb(root: Path) -> FixtureKB:
    """Create 2 processed docs, 4 chunks, 3 entities, 2 relations, 1 concept."""
    chunks = root / "chunks"
    concepts = root / "concepts"
    graphs = root / "graphs"
    summaries = root / "summaries"
    markdown = root / "markdown"
    for directory in (chunks, concepts, graphs, summaries, markdown):
        directory.mkdir(parents=True, exist_ok=True)

    index = """\
documents:
  - doc_id: usrdata-universe-notes
    title: Usrdata Universe Notes
    concepts:
      - qaid
    chunk_files:
      - chunks/usrdata-universe-notes-chunk-001.md
      - chunks/usrdata-universe-notes-chunk-002.md
    status: processed
    markdown_file: markdown/usrdata-universe-notes.md
    summary_file: summaries/usrdata-universe-notes.md
  - doc_id: barra-id-mapping
    title: Barra ID Mapping
    concepts:
      - identifier-mapping
    chunk_files:
      - chunks/barra-id-mapping-chunk-001.md
      - chunks/barra-id-mapping-chunk-002.md
    status: processed
    markdown_file: markdown/barra-id-mapping.md
    summary_file: summaries/barra-id-mapping.md
  - doc_id: draft-skipped-doc
    title: Draft Notes
    concepts:
      - secret-draft-token
    chunk_files:
      - chunks/draft-skipped-doc-chunk-001.md
    status: draft
    markdown_file: markdown/draft-skipped-doc.md
    summary_file: summaries/draft-skipped-doc.md
"""
    (root / "index.yaml").write_text(index, encoding="utf-8")

    graph = {
        "version": "1.0",
        "generated_at": "2026-08-18T00:00:00Z",
        "entities": [
            {
                "id": ENTITY_QAID,
                "label": "QAID",
                "type": "concept",
                "source_chunks": [CHUNK_NOTES_1],
            },
            {
                "id": ENTITY_BARRA,
                "label": "Barra ID",
                "type": "concept",
                "source_chunks": [CHUNK_BARRA_1],
            },
            {
                "id": ENTITY_DS,
                "label": "DS Regional ID",
                "type": "concept",
                "source_chunks": [CHUNK_BARRA_2],
            },
        ],
        "relations": [
            {
                "from": ENTITY_QAID,
                "to": ENTITY_BARRA,
                "type": "related_to",
                "source_chunk": CHUNK_NOTES_1,
            },
            {
                "from": ENTITY_BARRA,
                "to": ENTITY_DS,
                "type": "related_to",
                "source_chunk": CHUNK_BARRA_1,
            },
        ],
    }
    graph_path = graphs / "knowledge-graph.json"
    graph_path.write_bytes(json.dumps(graph).encode("utf-8"))

    (chunks / f"{CHUNK_NOTES_1}.md").write_text(
        _md(
            f"""
chunk_id: {CHUNK_NOTES_1}
doc_id: {DOC_NOTES}
title: QAID identifier
semantic_key: qaid-identifier
keywords:
  - qaid
  - identifier
potential_questions:
  - What is qaid?
entities:
  - qaid
summary: QAID is the QA Direct identifier used as a join key.
""",
            "QAID joins the security master to price and returns rows.",
        ),
        encoding="utf-8",
    )
    (chunks / f"{CHUNK_NOTES_2}.md").write_text(
        _md(
            f"""
chunk_id: {CHUNK_NOTES_2}
doc_id: {DOC_NOTES}
title: Universe construction notes
semantic_key: usrdata-universe
keywords:
  - universe
  - usrdata
potential_questions:
  - How is the universe built?
entities:
  - qaid
summary: Notes on building the usrdata universe.
""",
            "Universe membership is derived from processed security master rows.",
        ),
        encoding="utf-8",
    )
    (chunks / f"{CHUNK_BARRA_1}.md").write_text(
        _md(
            f"""
chunk_id: {CHUNK_BARRA_1}
doc_id: {DOC_BARRA}
title: Barra ID mapping
semantic_key: barra-id-mapping
keywords:
  - barra-id
  - mapping
potential_questions:
  - How does barra-id map to qaid?
entities:
  - barra-id
  - qaid
summary: Barra ID maps to QAID at regional grain.
""",
            "barra-id lives at grain=regional and maps from qaid.",
        ),
        encoding="utf-8",
    )
    (chunks / f"{CHUNK_BARRA_2}.md").write_text(
        _md(
            f"""
chunk_id: {CHUNK_BARRA_2}
doc_id: {DOC_BARRA}
title: DS Regional ID
semantic_key: ds-regional-id
keywords:
  - ds-regional-id
potential_questions:
  - What is ds-regional-id?
entities:
  - ds-regional-id
summary: DS regional identifier used with barra-id.
""",
            "ds-regional-id is two hops from qaid via barra-id.",
        ),
        encoding="utf-8",
    )
    (chunks / f"{CHUNK_SKIPPED}.md").write_text(
        _md(
            f"""
chunk_id: {CHUNK_SKIPPED}
doc_id: {DOC_SKIPPED}
title: Secret draft
semantic_key: {SKIPPED_TOKEN}
keywords:
  - {SKIPPED_TOKEN}
entities: []
summary: Should never be retrieved while status is draft.
""",
            f"This draft mentions {SKIPPED_TOKEN} and must be skipped.",
        ),
        encoding="utf-8",
    )
    (chunks / f"{CHUNK_DECOY}.md").write_text(
        _md(
            f"""
chunk_id: {CHUNK_DECOY}
doc_id: not-a-catalog-doc
title: Decoy chunk
semantic_key: {DECOY_TOKEN}
keywords:
  - {DECOY_TOKEN}
entities: []
summary: Not listed in catalog or graph source_chunks.
""",
            f"Decoy body {DECOY_TOKEN} must never be a candidate via glob.",
        ),
        encoding="utf-8",
    )

    (concepts / f"{CONCEPT_QAID}.md").write_text(
        _md(
            """
title: QAID
slug: qaid
""",
            "QAID (QA Direct ID) is the join key between the security master and prices.",
        ),
        encoding="utf-8",
    )
    (summaries / f"{DOC_NOTES}.md").write_text("# notes\n", encoding="utf-8")
    (summaries / f"{DOC_BARRA}.md").write_text("# barra\n", encoding="utf-8")
    (markdown / f"{DOC_NOTES}.md").write_text("# notes\n", encoding="utf-8")
    (markdown / f"{DOC_BARRA}.md").write_text("# barra\n", encoding="utf-8")

    return FixtureKB(root=root, index_path=root / "index.yaml", graph_path=graph_path)


@dataclass(slots=True)
class CliResult:
    code: int
    stdout: str
    stderr: str

    def stdout_json(self) -> Any:
        return json.loads(self.stdout)

    def stderr_json(self) -> Any:
        return json.loads(self.stderr)


def run_cli(argv: list[str]) -> CliResult:
    """Invoke kb_rag.cli.main with captured stdio.

    Accepts either a returned int or SystemExit.
    """
    from kb_rag.cli import main

    out = io.StringIO()
    err = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            result = main(argv)
            if isinstance(result, int):
                code = result
        except SystemExit as exc:
            raw = exc.code
            if raw is None:
                code = 0
            elif isinstance(raw, int):
                code = raw
            else:
                code = 1
    return CliResult(code=code, stdout=out.getvalue(), stderr=err.getvalue())


def collect_strings(obj: object) -> set[str]:
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, str):
            found.add(node)
        elif isinstance(node, dict):
            for key, val in node.items():
                if isinstance(key, str):
                    found.add(key)
                walk(val)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
        else:
            for attr in ("id", "chunk_id", "doc_id", "path", "kind", "body"):
                if hasattr(node, attr):
                    val = getattr(node, attr)
                    if isinstance(val, str):
                        found.add(val)
                    elif isinstance(val, (list, tuple, dict)):
                        walk(val)

    walk(obj)
    return found


def neighbor_ids_from_payload(payload: object) -> set[str]:
    ids: set[str] = set()
    if isinstance(payload, dict):
        raw = payload.get("neighbors", payload)
    else:
        raw = getattr(payload, "neighbors", payload)
    if isinstance(raw, dict):
        raw = raw.get("neighbors", [])
    if not isinstance(raw, (list, tuple)):
        return collect_strings(payload)
    for item in raw:
        if isinstance(item, str):
            ids.add(item)
        elif isinstance(item, dict):
            nid = item.get("id")
            if isinstance(nid, str):
                ids.add(nid)
        else:
            nid = getattr(item, "id", None)
            if isinstance(nid, str):
                ids.add(nid)
    return ids


class _BlockSentenceTransformers:
    def find_spec(self, fullname: str, path: object, target: object = None):  # noqa: ANN001
        if fullname == "sentence_transformers" or fullname.startswith(
            "sentence_transformers."
        ):
            raise ImportError("sentence_transformers blocked by test")
        return None


def block_sentence_transformers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force embeddings extra to look missing."""
    for key in list(sys.modules):
        if key == "sentence_transformers" or key.startswith("sentence_transformers."):
            monkeypatch.delitem(sys.modules, key, raising=False)
    finder = _BlockSentenceTransformers()
    monkeypatch.setattr(sys, "meta_path", [finder, *sys.meta_path])
    embeddings = sys.modules.get("kb_rag.scoring.embeddings")
    if embeddings is not None:
        importlib.reload(embeddings)


class OpenCounter:
    """Count opens of files under a chunks/ directory."""

    def __init__(self) -> None:
        self.chunk_paths: list[Path] = []

    def _record(self, file: object) -> None:
        try:
            path = Path(file)  # type: ignore[arg-type]
        except TypeError:
            return
        try:
            parts = path.parts
        except Exception:
            return
        if "chunks" in parts and path.suffix == ".md":
            self.chunk_paths.append(path)

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        orig_path_open = Path.open
        orig_io_open = io.open
        orig_os_open = os.open
        counter = self

        def path_open_bound(self: Path, *args: object, **kwargs: object):
            counter._record(self)
            return orig_path_open(self, *args, **kwargs)

        def io_open_bound(file: object, *args: object, **kwargs: object):
            counter._record(file)
            return orig_io_open(file, *args, **kwargs)

        def os_open_bound(path: object, *args: object, **kwargs: object):
            counter._record(path)
            return orig_os_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", path_open_bound)
        monkeypatch.setattr(io, "open", io_open_bound)
        monkeypatch.setattr("builtins.open", io_open_bound)
        monkeypatch.setattr(os, "open", os_open_bound)

    @property
    def unique_names(self) -> set[str]:
        return {Path(p).name for p in self.chunk_paths}


class GlobSpy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        orig_glob = Path.glob
        orig_rglob = Path.rglob
        spy = self

        def glob_bound(self: Path, pattern: str, *args: object, **kwargs: object):
            if self.name == "chunks" or "chunks" in self.parts:
                spy.calls.append((str(self), pattern))
            return orig_glob(self, pattern, *args, **kwargs)

        def rglob_bound(self: Path, pattern: str, *args: object, **kwargs: object):
            if self.name == "chunks" or "chunks" in self.parts:
                spy.calls.append((str(self), f"rglob:{pattern}"))
            return orig_rglob(self, pattern, *args, **kwargs)

        orig_walk = os.walk

        def walk_bound(top: object, *args: object, **kwargs: object):
            top_path = Path(str(top))
            if top_path.name == "chunks" or "chunks" in top_path.parts:
                spy.calls.append((str(top), "os.walk"))
            return orig_walk(top, *args, **kwargs)

        monkeypatch.setattr(Path, "glob", glob_bound)
        monkeypatch.setattr(Path, "rglob", rglob_bound)
        monkeypatch.setattr(os, "walk", walk_bound)
