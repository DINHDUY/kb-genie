from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from kb_rag.catalog import load_catalog
from kb_rag.models import Chunk, Document, KbRagError
from kb_rag.paths import resolve_kb_root

try:
    from yaml import CSafeLoader as _Loader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as _Loader


def _as_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    close = text.find("\n---", 3)
    if close == -1:
        return "", text
    yaml_slice = text[3:close].lstrip("\n")
    body = text[close + 4 :]
    if body.startswith("\n"):
        body = body[1:]
    return yaml_slice, body


def list_docs(kb_root: str | Path) -> list[Document]:
    resolved = resolve_kb_root(kb_root)
    catalog = load_catalog(resolved.index_path)
    return list(catalog.values())


def get_doc(kb_root: str | Path, doc_id: str) -> Document:
    resolved = resolve_kb_root(kb_root)
    catalog = load_catalog(resolved.index_path)
    doc = catalog.get(doc_id)
    if doc is None:
        raise KbRagError(f"document not found: {doc_id}", code="not_found")
    return doc


def get_chunk(kb_root: str | Path, chunk_id: str, *, include_body: bool = True) -> Chunk:
    resolved = resolve_kb_root(kb_root)
    rel = f"chunks/{chunk_id}.md"
    path = resolved.root / rel
    if not path.is_file():
        raise KbRagError(f"chunk not found: {chunk_id}", code="not_found")
    text = path.read_text(encoding="utf-8")
    yaml_slice, body = _split_frontmatter(text)
    meta = yaml.load(yaml_slice, Loader=_Loader) or {}
    if not isinstance(meta, dict):
        meta = {}
    return Chunk(
        chunk_id=str(meta.get("chunk_id") or chunk_id),
        doc_id=str(meta.get("doc_id") or ""),
        path=rel,
        title=meta.get("title"),
        semantic_key=meta.get("semantic_key"),
        keywords=_as_tuple(meta.get("keywords")),
        potential_questions=_as_tuple(meta.get("potential_questions")),
        entities=_as_tuple(meta.get("entities")),
        summary=meta.get("summary"),
        body=body if include_body else None,
    )


def get_concept(kb_root: str | Path, concept_id: str) -> dict[str, Any]:
    resolved = resolve_kb_root(kb_root)
    rel = f"concepts/{concept_id}.md"
    path = resolved.root / rel
    if not path.is_file():
        raise KbRagError(f"concept not found: {concept_id}", code="not_found")
    text = path.read_text(encoding="utf-8")
    yaml_slice, body = _split_frontmatter(text)
    meta = yaml.load(yaml_slice, Loader=_Loader) or {}
    payload: dict[str, Any] = dict(meta) if isinstance(meta, dict) else {}
    payload["id"] = concept_id
    payload["path"] = rel
    payload["body"] = body
    return payload
