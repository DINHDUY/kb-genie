"""Correctness tests for retrieve-only kb-rag.

Tests cover functional requirements and edge cases from spec.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from helpers import (
    CHUNK_BARRA_1,
    CHUNK_DECOY,
    CHUNK_NOTES_1,
    CHUNK_NOTES_2,
    CHUNK_SKIPPED,
    CONCEPT_QAID,
    DECOY_TOKEN,
    DOC_BARRA,
    DOC_NOTES,
    DOC_SKIPPED,
    ENTITY_BARRA,
    ENTITY_DS,
    ENTITY_QAID,
    SKIPPED_TOKEN,
    GlobSpy,
    block_sentence_transformers,
    collect_strings,
    neighbor_ids_from_payload,
    run_cli,
)


class TestMissingArtifacts:
    def test_edge01_missing_index_cli(self, tmp_path: Path) -> None:
        """EDGE-01 / FR-04: Missing index.yaml → non-zero exit and JSON stderr."""
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "graphs").mkdir()
        (kb / "graphs" / "knowledge-graph.json").write_text(
            '{"version":"1.0","entities":[],"relations":[]}', encoding="utf-8"
        )
        result = run_cli(["--kb-root", str(kb), "search", "qaid"])
        assert result.code != 0
        payload = result.stderr_json()
        assert isinstance(payload, dict)
        assert payload.get("code") == "missing_index"
        assert "error" in payload

    def test_edge02_missing_graph_cli(self, tmp_path: Path) -> None:
        """EDGE-02 / FR-04: Missing graph → non-zero exit and JSON stderr."""
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "index.yaml").write_text("documents: []\n", encoding="utf-8")
        result = run_cli(["--kb-root", str(kb), "retrieve", "qaid"])
        assert result.code != 0
        payload = result.stderr_json()
        assert isinstance(payload, dict)
        assert payload.get("code") == "missing_graph"
        assert "error" in payload

    def test_fr04_missing_index_resolve(self, tmp_path: Path) -> None:
        """FR-04: KnowledgeBaseRoot.resolve raises KbRagError for missing index."""
        from kb_rag.models import KbRagError
        from kb_rag.paths import KnowledgeBaseRoot

        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "graphs").mkdir()
        (kb / "graphs" / "knowledge-graph.json").write_text("{}", encoding="utf-8")
        with pytest.raises(KbRagError) as exc:
            KnowledgeBaseRoot.resolve(kb)
        assert exc.value.code == "missing_index"

    def test_fr04_missing_graph_resolve(self, tmp_path: Path) -> None:
        """FR-04: KnowledgeBaseRoot.resolve raises KbRagError when both graph paths missing."""
        from kb_rag.models import KbRagError
        from kb_rag.paths import KnowledgeBaseRoot

        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "index.yaml").write_text("documents: []\n", encoding="utf-8")
        with pytest.raises(KbRagError) as exc:
            KnowledgeBaseRoot.resolve(kb)
        assert exc.value.code == "missing_graph"


class TestCatalogConceptSearch:
    def test_fr09_concept_query_returns_doc_chunks(self, kb_root: Path) -> None:
        """FR-09: Query matching catalog concept qaid returns that doc's chunks."""
        from kb_rag.retrieve import search

        hits = search(kb_root, "what is qaid", top_k=8, rerank=False)
        ids = collect_strings(hits)
        assert CHUNK_NOTES_1 in ids
        assert CHUNK_NOTES_2 in ids

    def test_fr09_cli_search_concept(self, kb_root: Path) -> None:
        """FR-09 / FR-01: CLI search for qaid includes usrdata-universe-notes chunks."""
        result = run_cli(["--kb-root", str(kb_root), "search", "what is qaid"])
        assert result.code == 0
        payload = result.stdout_json()
        ids = collect_strings(payload)
        assert CHUNK_NOTES_1 in ids
        assert CHUNK_NOTES_2 in ids


class TestGraphExpansion:
    def test_fr10_neighbor_source_chunks_in_retrieve(self, kb_root: Path) -> None:
        """FR-10: 1-hop expansion includes related entity source_chunks."""
        from kb_rag.retrieve import retrieve

        pack = retrieve(kb_root, "qaid", top_k=8, rerank=False, hops=1)
        ids = collect_strings(pack)
        assert CHUNK_NOTES_1 in ids
        assert CHUNK_BARRA_1 in ids

    def test_edge10_two_hop_not_required(self, kb_root: Path) -> None:
        """EDGE-10: Default 1 hop does not require 2-hop entity ds-regional-id as a neighbor hit."""
        result = run_cli(
            ["--kb-root", str(kb_root), "neighbors", ENTITY_QAID, "--hops", "1"]
        )
        assert result.code == 0
        payload = result.stdout_json()
        ids = neighbor_ids_from_payload(payload)
        assert ENTITY_BARRA in ids
        assert ENTITY_DS not in ids
        assert ENTITY_QAID not in ids

    def test_fr10_two_hops_includes_ds(self, kb_root: Path) -> None:
        """FR-10: neighbors --hops 2 reaches ds-regional-id."""
        result = run_cli(
            ["--kb-root", str(kb_root), "neighbors", ENTITY_QAID, "--hops", "2"]
        )
        assert result.code == 0
        ids = neighbor_ids_from_payload(result.stdout_json())
        assert ENTITY_BARRA in ids
        assert ENTITY_DS in ids


class TestRoundTrip:
    def test_fr11_get_chunk_round_trip(self, kb_root: Path) -> None:
        """FR-11: get-chunk returns id and body text."""
        from kb_rag.store import get_chunk

        chunk = get_chunk(kb_root, CHUNK_NOTES_1, include_body=True)
        assert chunk.chunk_id == CHUNK_NOTES_1
        assert chunk.doc_id == DOC_NOTES
        assert chunk.body is not None
        assert "QAID" in chunk.body or "qaid" in chunk.body.lower()

        result = run_cli(["--kb-root", str(kb_root), "get-chunk", CHUNK_NOTES_1])
        assert result.code == 0
        payload = result.stdout_json()
        assert isinstance(payload, dict)
        assert payload.get("chunk_id") == CHUNK_NOTES_1
        assert "QA Direct" in str(payload.get("body", "")) or "qaid" in str(
            payload.get("body", "")
        ).lower()

    def test_fr11_get_concept_round_trip(self, kb_root: Path) -> None:
        """FR-11: get-concept returns id, path, and concept body."""
        from kb_rag.store import get_concept

        concept = get_concept(kb_root, CONCEPT_QAID)
        assert concept["id"] == CONCEPT_QAID
        assert "path" in concept
        assert "join key" in concept["body"]

        result = run_cli(["--kb-root", str(kb_root), "get-concept", CONCEPT_QAID])
        assert result.code == 0
        payload = result.stdout_json()
        assert isinstance(payload, dict)
        assert payload.get("id") == CONCEPT_QAID
        assert "join key" in payload.get("body", "")


class TestRerankDegrades:
    def test_fr13_rerank_without_extras(self, kb_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """FR-13 / EDGE-08: --rerank without sentence-transformers degrades to lexical."""
        block_sentence_transformers(monkeypatch)
        result = run_cli(
            ["--kb-root", str(kb_root), "--rerank", "search", "qaid"]
        )
        assert result.code == 0
        payload = result.stdout_json()
        ids = collect_strings(payload)
        assert CHUNK_NOTES_1 in ids


class TestSkipStatus:
    def test_fr05_skip_unprocessed_in_list_docs(self, kb_root: Path) -> None:
        """FR-05: list-docs omits status != processed."""
        from kb_rag.store import list_docs

        docs = list_docs(kb_root)
        ids = {d.doc_id for d in docs}
        assert DOC_NOTES in ids
        assert DOC_BARRA in ids
        assert DOC_SKIPPED not in ids

    def test_fr05_skipped_token_not_retrieved(self, kb_root: Path) -> None:
        """FR-05 / EDGE-06: draft concept token does not return skipped chunk."""
        from kb_rag.retrieve import search

        hits = search(kb_root, SKIPPED_TOKEN, top_k=8, rerank=False)
        ids = collect_strings(hits)
        assert CHUNK_SKIPPED not in ids
        assert DOC_SKIPPED not in ids


class TestNoGlobCandidates:
    def test_fr06_decoy_never_candidate(self, kb_root: Path) -> None:
        """FR-06 / EDGE-07: decoy chunk not listed in catalog/graph is not a hit."""
        from kb_rag.retrieve import search

        hits = search(kb_root, DECOY_TOKEN, top_k=8, rerank=False)
        ids = collect_strings(hits)
        assert CHUNK_DECOY not in ids

    def test_fr06_glob_not_used_on_chunks(
        self, kb_root: Path, glob_spy: GlobSpy
    ) -> None:
        """FR-06: retrieve must not glob/rglob/walk chunks/ to discover candidates."""
        from kb_rag.retrieve import retrieve

        retrieve(kb_root, "qaid", top_k=8, rerank=False)
        assert glob_spy.calls == []


class TestCliCommands:
    def test_fr01_search(self, kb_root: Path) -> None:
        """FR-01: search command emits JSON hits on stdout."""
        result = run_cli(["--kb-root", str(kb_root), "search", "qaid"])
        assert result.code == 0
        payload = result.stdout_json()
        assert isinstance(payload, dict)
        assert payload.get("query") == "qaid"
        assert "hits" in payload

    def test_fr01_retrieve(self, kb_root: Path) -> None:
        """FR-01: retrieve command emits pack JSON with citations."""
        result = run_cli(
            ["--kb-root", str(kb_root), "retrieve", "qaid", "--top-k", "8"]
        )
        assert result.code == 0
        payload = result.stdout_json()
        assert isinstance(payload, dict)
        assert "chunks" in payload
        assert "citations" in payload
        assert "concepts" in payload
        assert "neighbors" in payload
        citations = payload["citations"]
        assert isinstance(citations, list)
        if citations:
            assert "doc_id" in citations[0]
            assert "chunk_id" in citations[0]
            assert "path" in citations[0]

    def test_fr01_get_doc(self, kb_root: Path) -> None:
        """FR-01 / FR-12: get-doc returns processed catalog record."""
        result = run_cli(["--kb-root", str(kb_root), "get-doc", DOC_NOTES])
        assert result.code == 0
        payload = result.stdout_json()
        assert payload.get("doc_id") == DOC_NOTES
        assert payload.get("status") == "processed"
        assert CONCEPT_QAID in payload.get("concepts", [])

    def test_fr01_get_chunk(self, kb_root: Path) -> None:
        """FR-01: get-chunk CLI."""
        result = run_cli(["--kb-root", str(kb_root), "get-chunk", CHUNK_BARRA_1])
        assert result.code == 0
        assert result.stdout_json().get("chunk_id") == CHUNK_BARRA_1

    def test_fr01_get_concept(self, kb_root: Path) -> None:
        """FR-01: get-concept CLI."""
        result = run_cli(["--kb-root", str(kb_root), "get-concept", CONCEPT_QAID])
        assert result.code == 0
        assert result.stdout_json().get("id") == CONCEPT_QAID

    def test_fr01_neighbors(self, kb_root: Path) -> None:
        """FR-01: neighbors CLI."""
        result = run_cli(["--kb-root", str(kb_root), "neighbors", ENTITY_QAID])
        assert result.code == 0
        payload = result.stdout_json()
        assert payload.get("id") == ENTITY_QAID
        assert payload.get("hops") == 1
        assert ENTITY_BARRA in neighbor_ids_from_payload(payload)

    def test_fr01_list_docs(self, kb_root: Path) -> None:
        """FR-01 / FR-12: list-docs CLI JSON."""
        result = run_cli(["--kb-root", str(kb_root), "list-docs"])
        assert result.code == 0
        payload = result.stdout_json()
        docs = payload.get("documents")
        assert isinstance(docs, list)
        ids = {d["doc_id"] for d in docs}
        assert ids == {DOC_NOTES, DOC_BARRA}

    def test_fr03_json_stdout_compact(self, kb_root: Path) -> None:
        """FR-03: JSON stdout uses compact separators (no spaces after : or ,)."""
        result = run_cli(["--kb-root", str(kb_root), "list-docs"])
        assert result.code == 0
        raw = result.stdout.strip()
        json.loads(raw)
        assert ": " not in raw
        assert ", " not in raw

    def test_fr03_errors_json_on_stderr_not_stdout(self, tmp_path: Path) -> None:
        """FR-03: errors are JSON on stderr; stdout is not the error object."""
        kb = tmp_path / "empty"
        kb.mkdir()
        result = run_cli(["--kb-root", str(kb), "search", "qaid"])
        assert result.code != 0
        err = result.stderr_json()
        assert isinstance(err, dict)
        assert "error" in err
        if result.stdout.strip():
            try:
                out = json.loads(result.stdout)
            except json.JSONDecodeError:
                out = None
            if isinstance(out, dict):
                assert "error" not in out

    def test_fr02_kb_root_env(self, kb_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """FR-02: KB_ROOT env is accepted when --kb-root is omitted."""
        monkeypatch.setenv("KB_ROOT", str(kb_root))
        result = run_cli(["list-docs"])
        assert result.code == 0
        ids = {d["doc_id"] for d in result.stdout_json()["documents"]}
        assert DOC_NOTES in ids

    def test_edge04_empty_query(self, kb_root: Path) -> None:
        """EDGE-04: empty query exits 0 (hits may be empty)."""
        result = run_cli(["--kb-root", str(kb_root), "search", ""])
        assert result.code == 0
        payload = result.stdout_json()
        assert "hits" in payload

    def test_edge05_unknown_chunk(self, kb_root: Path) -> None:
        """EDGE-05: unknown get-chunk id → not_found."""
        result = run_cli(["--kb-root", str(kb_root), "get-chunk", "no-such-chunk"])
        assert result.code != 0
        assert result.stderr_json().get("code") == "not_found"

    def test_edge12_unknown_neighbor_id(self, kb_root: Path) -> None:
        """EDGE-12: neighbors of unknown id → empty list, exit 0."""
        result = run_cli(["--kb-root", str(kb_root), "neighbors", "no-such-entity"])
        assert result.code == 0
        assert neighbor_ids_from_payload(result.stdout_json()) == set()

    def test_fr18_models_are_slotted_not_frozen(self) -> None:
        """FR-18: Document/Chunk/Entity/Hit/RetrievalPack use slots, not frozen."""
        from kb_rag.models import Chunk, Document, Entity, Hit, RetrievalPack

        for cls in (Document, Chunk, Entity, Hit, RetrievalPack):
            assert getattr(cls, "__slots__", ()) != ()
            params = getattr(cls, "__dataclass_params__", None)
            assert params is not None, f"{cls.__name__} must be a dataclass"
            assert not params.frozen


class TestLibraryHelpers:
    def test_catalog_drops_skipped(self, kb_root: Path) -> None:
        """FR-05: load_catalog omits draft documents."""
        from kb_rag.catalog import load_catalog
        from kb_rag.paths import KnowledgeBaseRoot

        resolved = KnowledgeBaseRoot.resolve(kb_root)
        catalog = load_catalog(resolved.index_path)
        assert DOC_SKIPPED not in catalog
        assert DOC_NOTES in catalog
        notes = catalog[DOC_NOTES]
        assert CHUNK_NOTES_1 in notes.chunk_files
        assert "chunks/" not in notes.chunk_files[0]

    def test_catalog_accepts_top_level_document_list(self, tmp_path: Path) -> None:
        """kb-genie index.yaml is a YAML list of documents, not {documents: [...]}."""
        from kb_rag.catalog import load_catalog

        index = tmp_path / "index.yaml"
        index.write_text(
            "- doc_id: usrdata-universe-notes\n"
            "  title: Notes\n"
            "  status: processed\n"
            "  concepts: [qaid]\n"
            "  chunk_files:\n"
            "    - chunks/usrdata-universe-notes-chunk-001.md\n",
            encoding="utf-8",
        )
        catalog = load_catalog(index)
        assert "usrdata-universe-notes" in catalog
        assert catalog["usrdata-universe-notes"].chunk_files == (
            "usrdata-universe-notes-chunk-001",
        )

    def test_graph_neighbors_undirected(self, kb_root: Path) -> None:
        """FR-10: adjacency is undirected (barra-id lists qaid)."""
        from kb_rag.graph import load_graph, neighbors
        from kb_rag.paths import KnowledgeBaseRoot

        resolved = KnowledgeBaseRoot.resolve(kb_root)
        graph = load_graph(resolved.graph_path)
        assert ENTITY_QAID in neighbors(graph, ENTITY_BARRA, hops=1)
        assert CHUNK_BARRA_1 in graph.entities[ENTITY_BARRA].source_chunks
