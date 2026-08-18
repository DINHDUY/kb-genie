from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from kb_rag.models import Document, KbRagError

try:
    from yaml import CSafeLoader as _Loader
except ImportError:  # pragma: no cover - LibYAML missing
    from yaml import SafeLoader as _Loader


def _chunk_id(raw: str) -> str:
    value = raw.replace("\\", "/")
    if value.startswith("chunks/"):
        value = value[7:]
    if value.endswith(".md"):
        value = value[:-3]
    return value


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _document_rows(payload: Any) -> list[Any]:
    """kb-genie index.yaml is a document list; also accept {documents: [...]}."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        rows = payload.get("documents")
        if rows is None:
            return []
        if isinstance(rows, list):
            return rows
        raise KbRagError("index.yaml documents must be a list", code="invalid_index")
    raise KbRagError("index.yaml must be a document list or a documents mapping", code="invalid_index")


def load_catalog(index_path: Path) -> dict[str, Document]:
    """Processed documents only, keyed by doc_id. OPT-01: CSafeLoader, never safe_load."""
    with index_path.open("r", encoding="utf-8") as stream:
        payload = yaml.load(stream, Loader=_Loader)
    documents = _document_rows(payload)
    catalog: dict[str, Document] = {}
    for row in documents:
        if not isinstance(row, dict):
            continue
        if row.get("status") != "processed":
            continue
        doc_id = str(row.get("doc_id", ""))
        if not doc_id:
            continue
        chunk_files = tuple(_chunk_id(str(item)) for item in (row.get("chunk_files") or []))
        catalog[doc_id] = Document(
            doc_id=doc_id,
            title=str(row.get("title") or ""),
            concepts=_as_str_tuple(row.get("concepts")),
            chunk_files=chunk_files,
            status="processed",
            markdown_file=row.get("markdown_file"),
            summary_file=row.get("summary_file"),
        )
    return catalog
