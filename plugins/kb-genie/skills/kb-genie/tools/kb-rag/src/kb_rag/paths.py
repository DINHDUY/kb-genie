from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kb_rag.models import KbRagError


@dataclass(slots=True)
class KnowledgeBaseRoot:
    root: Path
    index_path: Path
    graph_path: Path

    @classmethod
    def resolve(cls, kb_root: str | Path) -> KnowledgeBaseRoot:
        """Stat index.yaml and canonical/fallback graph. Raise KbRagError if missing."""
        root = Path(kb_root)
        index_path = root / "index.yaml"
        if not index_path.is_file():
            raise KbRagError("index.yaml not found", code="missing_index")
        canonical = root / "graphs" / "knowledge-graph.json"
        fallback = root / "graph" / "knowledge-graph.json"
        if canonical.is_file():
            graph_path = canonical
        elif fallback.is_file():
            graph_path = fallback
        else:
            raise KbRagError("knowledge-graph.json not found", code="missing_graph")
        return cls(root=root, index_path=index_path, graph_path=graph_path)


def resolve_kb_root(kb_root: str | Path) -> KnowledgeBaseRoot:
    return KnowledgeBaseRoot.resolve(kb_root)
