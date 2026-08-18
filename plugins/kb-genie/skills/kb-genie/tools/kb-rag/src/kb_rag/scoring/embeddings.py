from __future__ import annotations

from collections.abc import Sequence

from kb_rag.models import Hit, Ranker

_ranker: Ranker | None = None
_ranker_loaded = False


class _MiniLMRanker:
    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def rerank(self, query: str, hits: Sequence[Hit], texts: Sequence[str]) -> list[Hit]:
        if not hits:
            return list(hits)
        vectors = self._model.encode(
            [query, *texts],
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        query_vec = vectors[0]
        scores = vectors[1:] @ query_vec
        paired = list(zip(hits, scores, strict=False))
        paired.sort(key=lambda item: float(item[1]), reverse=True)
        ranked: list[Hit] = []
        for hit, score in paired:
            hit.score = float(score)
            ranked.append(hit)
        return ranked


def get_ranker() -> Ranker | None:
    """None if sentence_transformers is unavailable. Lazy import only (OPT-09)."""
    global _ranker, _ranker_loaded
    if _ranker_loaded:
        return _ranker
    _ranker_loaded = True
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        _ranker = None
        return None
    _ranker = _MiniLMRanker()
    return _ranker
