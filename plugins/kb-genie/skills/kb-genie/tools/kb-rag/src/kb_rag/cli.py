from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from kb_rag.graph import load_graph, neighbors
from kb_rag.models import Chunk, Document, Entity, Hit, KbRagError, RetrievalPack
from kb_rag.paths import resolve_kb_root
from kb_rag.retrieve import retrieve, search
from kb_rag.store import get_chunk, get_concept, get_doc, list_docs

_JSON_SEP = (",", ":")


def _dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=_JSON_SEP)


def _doc_dict(doc: Document) -> dict[str, Any]:
    return {
        "doc_id": doc.doc_id,
        "title": doc.title,
        "concepts": list(doc.concepts),
        "chunk_files": list(doc.chunk_files),
        "status": doc.status,
    }


def _chunk_dict(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "path": chunk.path,
        "title": chunk.title,
        "semantic_key": chunk.semantic_key,
        "keywords": list(chunk.keywords),
        "potential_questions": list(chunk.potential_questions),
        "entities": list(chunk.entities),
        "summary": chunk.summary,
        "body": chunk.body,
        "score": chunk.score,
    }


def _hit_dict(hit: Hit) -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": hit.kind, "id": hit.id, "score": hit.score}
    if hit.doc_id is not None:
        payload["doc_id"] = hit.doc_id
    if hit.chunk_id is not None:
        payload["chunk_id"] = hit.chunk_id
    if hit.path is not None:
        payload["path"] = hit.path
    if hit.title is not None:
        payload["title"] = hit.title
    return payload


def _entity_dict(entity: Entity) -> dict[str, Any]:
    return {
        "id": entity.id,
        "label": entity.label,
        "type": entity.type,
        "source_chunks": list(entity.source_chunks),
    }


def _pack_dict(pack: RetrievalPack) -> dict[str, Any]:
    return {
        "query": pack.query,
        "chunks": [_chunk_dict(chunk) for chunk in pack.chunks],
        "concepts": pack.concepts,
        "neighbors": [_entity_dict(ent) for ent in pack.neighbors],
        "citations": pack.citations,
    }


def _write_text(stream: Any, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(text.encode("utf-8"))
        buffer.flush()
        return
    stream.write(text)


def _emit(payload: object, fmt: str) -> None:
    _write_text(sys.stdout, _dumps(payload) if fmt == "json" else _dumps(payload))


def _kb_root(args: argparse.Namespace) -> str:
    root = args.kb_root or os.environ.get("KB_ROOT")
    if not root:
        raise KbRagError("missing --kb-root or KB_ROOT", code="error")
    return root


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kb-rag")
    parser.add_argument("--kb-root", default=None)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--top-k", type=int, default=8)
    rerank = parser.add_mutually_exclusive_group()
    rerank.add_argument("--rerank", action="store_true", default=False)
    rerank.add_argument("--no-rerank", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search")
    p_search.add_argument("query", nargs="?", default="")
    p_search.add_argument("--top-k", type=int, default=None, dest="cmd_top_k")

    p_retrieve = sub.add_parser("retrieve")
    p_retrieve.add_argument("query", nargs="?", default="")
    p_retrieve.add_argument("--top-k", type=int, default=None, dest="cmd_top_k")

    p_get_doc = sub.add_parser("get-doc")
    p_get_doc.add_argument("doc_id")

    p_get_chunk = sub.add_parser("get-chunk")
    p_get_chunk.add_argument("chunk_id")

    p_get_concept = sub.add_parser("get-concept")
    p_get_concept.add_argument("concept_id")

    p_neighbors = sub.add_parser("neighbors")
    p_neighbors.add_argument("entity_id")
    p_neighbors.add_argument("--hops", type=int, default=1)

    sub.add_parser("list-docs")
    return parser


def _dispatch(args: argparse.Namespace) -> object:
    root = _kb_root(args)
    command = args.command
    top_k = getattr(args, "cmd_top_k", None) or args.top_k
    if command == "search":
        hits = search(root, args.query, top_k=top_k, rerank=args.rerank)
        return {"query": args.query, "hits": [_hit_dict(hit) for hit in hits]}
    if command == "retrieve":
        pack = retrieve(root, args.query, top_k=top_k, rerank=args.rerank)
        return _pack_dict(pack)
    if command == "get-doc":
        return _doc_dict(get_doc(root, args.doc_id))
    if command == "get-chunk":
        return _chunk_dict(get_chunk(root, args.chunk_id, include_body=True))
    if command == "get-concept":
        return get_concept(root, args.concept_id)
    if command == "neighbors":
        resolved = resolve_kb_root(root)
        graph = load_graph(resolved.graph_path)
        ids = neighbors(graph, args.entity_id, hops=args.hops)
        return {"id": args.entity_id, "hops": args.hops, "neighbors": ids}
    if command == "list-docs":
        return {"documents": [_doc_dict(doc) for doc in list_docs(root)]}
    raise KbRagError(f"unknown command: {command}", code="error")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
        payload = _dispatch(args)
        _emit(payload, args.format)
        return 0
    except KbRagError as exc:
        _write_text(sys.stderr, _dumps({"error": str(exc), "code": exc.code}))
        return exc.exit_code
