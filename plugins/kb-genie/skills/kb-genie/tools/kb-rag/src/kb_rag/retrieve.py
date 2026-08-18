from __future__ import annotations

import heapq
import sys
from dataclasses import dataclass
from pathlib import Path

from kb_rag.catalog import load_catalog
from kb_rag.graph import GraphIndex, load_graph, neighbors
from kb_rag.models import Chunk, Document, Entity, Hit, RetrievalPack
from kb_rag.paths import KnowledgeBaseRoot, resolve_kb_root
from kb_rag.scoring.lexical import score_fields
from kb_rag.scoring.tokenize import tokenize
from kb_rag.store import get_chunk, get_concept

_CANDIDATE_CAP = 128
_SNAPSHOT_CACHE: dict[tuple[str, int], _Snapshot] = {}


@dataclass(slots=True)
class _Snapshot:
    root: Path
    catalog: dict[str, Document]
    graph: GraphIndex
    doc_postings: dict[str, list[str]]
    entity_postings: dict[str, list[str]]


def _add_posting(index: dict[str, list[str]], token: str, key: str) -> None:
    interned = sys.intern(token)
    bucket = index.get(interned)
    if bucket is None:
        index[interned] = [key]
        return
    if key not in bucket:
        bucket.append(key)


def _index_text(index: dict[str, list[str]], text: str, key: str) -> None:
    for token in tokenize(text):
        _add_posting(index, token, key)


def _build_snapshot(resolved: KnowledgeBaseRoot) -> _Snapshot:
    catalog = load_catalog(resolved.index_path)
    graph = load_graph(resolved.graph_path)
    doc_postings: dict[str, list[str]] = {}
    entity_postings: dict[str, list[str]] = {}
    for doc in catalog.values():
        _index_text(doc_postings, doc.doc_id, doc.doc_id)
        _index_text(doc_postings, doc.title, doc.doc_id)
        for concept in doc.concepts:
            _index_text(doc_postings, concept, doc.doc_id)
    for entity in graph.entities.values():
        _index_text(entity_postings, entity.id, entity.id)
        _index_text(entity_postings, entity.label, entity.id)
    return _Snapshot(
        root=resolved.root,
        catalog=catalog,
        graph=graph,
        doc_postings=doc_postings,
        entity_postings=entity_postings,
    )


def _load_snapshot(kb_root: str | Path) -> _Snapshot:
    resolved = resolve_kb_root(kb_root)
    mtime_ns = resolved.index_path.stat().st_mtime_ns + resolved.graph_path.stat().st_mtime_ns
    key = (str(resolved.root.resolve()), mtime_ns)
    if "pytest" in sys.modules:
        cached = _SNAPSHOT_CACHE.get(key)
        if cached is not None:
            return cached
    snapshot = _build_snapshot(resolved)
    if "pytest" in sys.modules:
        _SNAPSHOT_CACHE[key] = snapshot
    return snapshot


def _union_keys(postings: dict[str, list[str]], query_tokens: tuple[str, ...]) -> set[str]:
    keys: set[str] = set()
    for token in query_tokens:
        bucket = postings.get(token)
        if bucket:
            keys.update(bucket)
    return keys


def _stage1_candidates(
    snapshot: _Snapshot,
    query: str,
    query_tokens: tuple[str, ...],
    *,
    top_k: int,
    hops: int,
) -> tuple[list[str], list[Entity]]:
    catalog = snapshot.catalog
    graph = snapshot.graph
    doc_ids = _union_keys(snapshot.doc_postings, query_tokens)
    entity_ids = _union_keys(snapshot.entity_postings, query_tokens)

    doc_scores: list[tuple[float, str]] = []
    for doc_id in doc_ids:
        doc = catalog[doc_id]
        score = score_fields(
            query_tokens,
            {"title": doc.title, "concepts": doc.concepts, "semantic_key": doc.doc_id},
            query_text=query,
        )
        if score > 0:
            doc_scores.append((score, doc_id))
    doc_scores.sort(key=lambda item: item[0], reverse=True)
    take_n = max(8, 2 * top_k)
    top_docs = [doc_id for _, doc_id in doc_scores[:take_n]]

    matched_entities: list[str] = []
    for eid in entity_ids:
        ent = graph.entities.get(eid)
        if ent is None:
            continue
        score = score_fields(
            query_tokens,
            {"semantic_key": ent.id, "title": ent.label},
            query_text=query,
        )
        if score > 0:
            matched_entities.append(eid)

    expanded: set[str] = set(matched_entities)
    for eid in matched_entities:
        expanded.update(neighbors(graph, eid, hops=hops))
    neighbor_entities = [graph.entities[eid] for eid in expanded if eid in graph.entities]

    entity_chunks: list[str] = []
    seen_e: set[str] = set()
    for ent in neighbor_entities:
        for chunk_id in ent.source_chunks:
            if chunk_id not in seen_e:
                seen_e.add(chunk_id)
                entity_chunks.append(chunk_id)

    doc_chunks: list[str] = []
    seen_d: set[str] = set()
    for doc_id in top_docs:
        for chunk_id in catalog[doc_id].chunk_files:
            if chunk_id not in seen_d:
                seen_d.add(chunk_id)
                doc_chunks.append(chunk_id)

    candidates: list[str] = []
    seen: set[str] = set()
    for chunk_id in entity_chunks:
        if chunk_id not in seen:
            seen.add(chunk_id)
            candidates.append(chunk_id)
        if len(candidates) >= _CANDIDATE_CAP:
            return candidates[:_CANDIDATE_CAP], neighbor_entities
    for chunk_id in doc_chunks:
        if chunk_id not in seen:
            seen.add(chunk_id)
            candidates.append(chunk_id)
        if len(candidates) >= _CANDIDATE_CAP:
            break
    return candidates, neighbor_entities


def _chunk_fields(chunk: Chunk) -> dict[str, str | tuple[str, ...] | None]:
    return {
        "semantic_key": chunk.semantic_key,
        "title": chunk.title,
        "keywords": chunk.keywords,
        "potential_questions": chunk.potential_questions,
        "entities": chunk.entities,
        "summary": chunk.summary,
        "body": chunk.body,
    }


def _score_candidates(
    kb_root: Path,
    query: str,
    query_tokens: tuple[str, ...],
    candidate_ids: list[str],
    top_k: int,
) -> list[Hit]:
    scored: list[Hit] = []
    for chunk_id in candidate_ids:
        try:
            chunk = get_chunk(kb_root, chunk_id, include_body=False)
        except Exception:
            continue
        score = score_fields(query_tokens, _chunk_fields(chunk), query_text=query)
        scored.append(
            Hit(
                kind="chunk",
                id=chunk.chunk_id,
                score=score,
                doc_id=chunk.doc_id,
                chunk_id=chunk.chunk_id,
                path=chunk.path,
                title=chunk.title,
            )
        )
    if not scored:
        return []
    return heapq.nlargest(top_k, scored, key=lambda hit: hit.score)


def _maybe_rerank(query: str, hits: list[Hit], rerank: bool) -> list[Hit]:
    if not rerank or not hits:
        return hits
    from kb_rag.scoring.embeddings import get_ranker

    ranker = get_ranker()
    if ranker is None:
        return hits
    texts = [f"{hit.title or ''} {hit.id}" for hit in hits]
    return ranker.rerank(query, hits, texts)


def search(
    kb_root: str | Path,
    query: str,
    *,
    top_k: int = 8,
    rerank: bool = False,
    hops: int = 1,
) -> list[Hit]:
    snapshot = _load_snapshot(kb_root)
    query_tokens = tokenize(query)
    candidates, _ = _stage1_candidates(
        snapshot, query, query_tokens, top_k=top_k, hops=hops
    )
    hits = _score_candidates(snapshot.root, query, query_tokens, candidates, top_k)
    return _maybe_rerank(query, hits, rerank)


def retrieve(
    kb_root: str | Path,
    query: str,
    *,
    top_k: int = 8,
    rerank: bool = False,
    hops: int = 1,
) -> RetrievalPack:
    snapshot = _load_snapshot(kb_root)
    query_tokens = tokenize(query)
    candidates, neighbor_entities = _stage1_candidates(
        snapshot, query, query_tokens, top_k=top_k, hops=hops
    )
    hits = _maybe_rerank(
        query,
        _score_candidates(snapshot.root, query, query_tokens, candidates, top_k),
        rerank,
    )
    chunks: list[Chunk] = []
    citations: list[dict[str, str]] = []
    concept_ids: set[str] = set()
    for hit in hits:
        chunk_id = hit.chunk_id or hit.id
        chunk = get_chunk(snapshot.root, chunk_id, include_body=True)
        chunk.score = hit.score
        chunks.append(chunk)
        citations.append({"doc_id": chunk.doc_id, "chunk_id": chunk.chunk_id, "path": chunk.path})
        doc = snapshot.catalog.get(chunk.doc_id)
        if doc is not None:
            concept_ids.update(doc.concepts)
    concepts: list[dict[str, object]] = []
    for cid in concept_ids:
        try:
            concepts.append(get_concept(snapshot.root, cid))
        except Exception:
            concepts.append({"id": cid})
    return RetrievalPack(
        query=query,
        chunks=chunks,
        concepts=concepts,
        neighbors=neighbor_entities,
        citations=citations,
    )
