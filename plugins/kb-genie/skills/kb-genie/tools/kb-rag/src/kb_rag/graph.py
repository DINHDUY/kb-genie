from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from kb_rag.models import Entity


class GraphIndex:
    def __init__(
        self,
        entities: dict[str, Entity],
        adjacency: dict[str, list[str]],
        path: Path,
    ) -> None:
        self.entities = entities
        self.adjacency = adjacency
        self.path = path


def _as_chunk_tuple(value: object) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)  # type: ignore[arg-type]


def load_graph(graph_path: Path) -> GraphIndex:
    """Parse graph JSON from bytes (OPT-02). Build undirected adjacency (BAN-07)."""
    payload = json.loads(graph_path.read_bytes())
    entities: dict[str, Entity] = {}
    for row in payload.get("entities") or []:
        if not isinstance(row, dict):
            continue
        eid = str(row.get("id", ""))
        if not eid:
            continue
        entities[eid] = Entity(
            id=eid,
            label=str(row.get("label") or ""),
            type=str(row.get("type") or ""),
            source_chunks=_as_chunk_tuple(row.get("source_chunks")),
        )
    adjacency: dict[str, list[str]] = {eid: [] for eid in entities}
    for rel in payload.get("relations") or []:
        if not isinstance(rel, dict):
            continue
        src = str(rel.get("from", ""))
        dst = str(rel.get("to", ""))
        if not src or not dst:
            continue
        adjacency.setdefault(src, [])
        adjacency.setdefault(dst, [])
        if dst not in adjacency[src]:
            adjacency[src].append(dst)
        if src not in adjacency[dst]:
            adjacency[dst].append(src)
    return GraphIndex(entities=entities, adjacency=adjacency, path=graph_path)


def neighbors(graph: GraphIndex, entity_id: str, hops: int = 1) -> list[str]:
    """BFS with deque + visited; hops<1 or unknown id → []. Exclude start id."""
    if hops < 1 or entity_id not in graph.adjacency:
        return []
    adj = graph.adjacency
    seen: set[str] = {entity_id}
    queue: deque[tuple[str, int]] = deque([(entity_id, 0)])
    found: list[str] = []
    while queue:
        current, depth = queue.popleft()
        if depth >= hops:
            continue
        for nxt in adj.get(current, ()):
            if nxt in seen:
                continue
            seen.add(nxt)
            found.append(nxt)
            queue.append((nxt, depth + 1))
    return found
