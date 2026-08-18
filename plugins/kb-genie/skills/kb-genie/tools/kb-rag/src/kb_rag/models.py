from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class KbRagError(Exception):
    """Fail-fast error. `code` is a stable machine key for CLI JSON."""

    def __init__(self, message: str, *, code: str = "error", exit_code: int = 1) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


@dataclass(slots=True)
class Document:
    doc_id: str
    title: str
    concepts: tuple[str, ...]
    chunk_files: tuple[str, ...]
    status: str
    markdown_file: str | None = None
    summary_file: str | None = None


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    path: str
    title: str | None
    semantic_key: str | None
    keywords: tuple[str, ...]
    potential_questions: tuple[str, ...]
    entities: tuple[str, ...]
    summary: str | None
    body: str | None
    score: float | None = None


@dataclass(slots=True)
class Entity:
    id: str
    label: str
    type: str
    source_chunks: tuple[str, ...]


@dataclass(slots=True)
class Hit:
    kind: str
    id: str
    score: float
    doc_id: str | None = None
    chunk_id: str | None = None
    path: str | None = None
    title: str | None = None


@dataclass(slots=True)
class RetrievalPack:
    query: str
    chunks: list[Chunk]
    concepts: list[dict[str, Any]]
    neighbors: list[Entity]
    citations: list[dict[str, str]]

    @property
    def chunk_id(self) -> tuple[str, ...]:
        return tuple(chunk.chunk_id for chunk in self.chunks)

    @property
    def id(self) -> tuple[str, ...]:
        return tuple(ent.id for ent in self.neighbors) + self.chunk_id

    @property
    def doc_id(self) -> tuple[str, ...]:
        return tuple(chunk.doc_id for chunk in self.chunks)

    @property
    def path(self) -> tuple[str, ...]:
        return tuple(chunk.path for chunk in self.chunks)

    @property
    def body(self) -> tuple[str, ...]:
        return tuple(chunk.body for chunk in self.chunks if chunk.body)


class Ranker(Protocol):
    def rerank(self, query: str, hits: Sequence[Hit], texts: Sequence[str]) -> list[Hit]: ...
