"""paths.py graph fallback tests (FR-04 / OPT-03 / EDGE-03)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kb_rag.models import KbRagError
from kb_rag.paths import KnowledgeBaseRoot, resolve_kb_root


def _write_index(root: Path) -> None:
    (root / "index.yaml").write_text("documents: []\n", encoding="utf-8")


def _write_graph(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps({"version": "1.0", "entities": [], "relations": []}).encode())


class TestGraphFallback:
    def test_fr04_canonical_graphs_path(self, tmp_path: Path) -> None:
        """FR-04: canonical graph is graphs/knowledge-graph.json."""
        root = tmp_path / "kb"
        root.mkdir()
        _write_index(root)
        canonical = root / "graphs" / "knowledge-graph.json"
        _write_graph(canonical)
        resolved = KnowledgeBaseRoot.resolve(root)
        assert resolved.index_path.resolve() == (root / "index.yaml").resolve()
        assert resolved.graph_path.resolve() == canonical.resolve()
        assert resolved.root.resolve() == root.resolve()

    def test_edge03_fallback_graph_dir(self, tmp_path: Path) -> None:
        """EDGE-03: graph/knowledge-graph.json is used when graphs/ is missing."""
        root = tmp_path / "kb"
        root.mkdir()
        _write_index(root)
        fallback = root / "graph" / "knowledge-graph.json"
        _write_graph(fallback)
        resolved = resolve_kb_root(root)
        assert resolved.graph_path.resolve() == fallback.resolve()

    def test_edge03_canonical_preferred_over_fallback(self, tmp_path: Path) -> None:
        """EDGE-03: graphs/ wins when both canonical and fallback exist."""
        root = tmp_path / "kb"
        root.mkdir()
        _write_index(root)
        canonical = root / "graphs" / "knowledge-graph.json"
        fallback = root / "graph" / "knowledge-graph.json"
        _write_graph(canonical)
        _write_graph(fallback)
        resolved = KnowledgeBaseRoot.resolve(root)
        assert resolved.graph_path.resolve() == canonical.resolve()

    def test_fr04_missing_both_graphs_raises(self, tmp_path: Path) -> None:
        """FR-04: neither graph path → missing_graph."""
        root = tmp_path / "kb"
        root.mkdir()
        _write_index(root)
        with pytest.raises(KbRagError) as exc:
            KnowledgeBaseRoot.resolve(root)
        assert exc.value.code == "missing_graph"

    def test_fr04_missing_index_raises(self, tmp_path: Path) -> None:
        """FR-04: missing index.yaml → missing_index even if graph exists."""
        root = tmp_path / "kb"
        root.mkdir()
        _write_graph(root / "graphs" / "knowledge-graph.json")
        with pytest.raises(KbRagError) as exc:
            KnowledgeBaseRoot.resolve(root)
        assert exc.value.code == "missing_index"

    def test_fr04_resolve_accepts_str_path(self, tmp_path: Path) -> None:
        """FR-04: resolve accepts str as well as Path."""
        root = tmp_path / "kb"
        root.mkdir()
        _write_index(root)
        _write_graph(root / "graphs" / "knowledge-graph.json")
        resolved = resolve_kb_root(str(root))
        assert resolved.root.resolve() == root.resolve()
