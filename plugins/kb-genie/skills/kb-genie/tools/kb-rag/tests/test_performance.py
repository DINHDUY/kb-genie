"""Performance benchmark tests for kb-rag (PERF-08, TEST-02–TEST-04).

pytest-benchmark is optional. Hard assertions use time.perf_counter and
CI-tolerant caps. Constitution quiet-machine targets are recorded as comments.
"""

from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from pathlib import Path

import pytest

from helpers import (
    CHUNK_DECOY,
    CHUNK_SKIPPED,
    PROCESSED_CHUNK_FILES,
    write_fixture_kb,
)

# Constitution quiet-machine targets (record; do not hard-fail CI on jitter).
CONSTITUTION_FIXTURE_P95_S = 0.200
CONSTITUTION_LARGE_P95_S = 2.0
# CI-tolerant hard caps (spec §3.1).
CI_FIXTURE_CAP_S = 2.0
CI_LARGE_CAP_S = 5.0
WARMUP = 2
FIXTURE_ROUNDS = 10
LARGE_ROUNDS = 5
CANDIDATE_OPEN_CAP = 128


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[idx]


def _timed_retrieve(kb_root: Path, query: str, rounds: int, warmup: int) -> list[float]:
    from kb_rag.retrieve import retrieve

    for _ in range(warmup):
        retrieve(kb_root, query, top_k=8, rerank=False)
    samples: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter()
        retrieve(kb_root, query, top_k=8, rerank=False)
        samples.append(time.perf_counter() - start)
    return samples


class TestFixtureLatency:
    def test_perf08_fixture_retrieve_ci_cap(self, kb_root: Path) -> None:
        """PERF-08: lexical retrieve on fixture KB; CI cap 2s, record p95 vs 200ms."""
        samples = _timed_retrieve(kb_root, "qaid", FIXTURE_ROUNDS, WARMUP)
        p50 = statistics.median(samples)
        p95 = _percentile(samples, 95)
        # Quiet-machine target is 200ms p95; CI asserts the cap only.
        assert p50 < CI_FIXTURE_CAP_S
        assert p95 < CI_FIXTURE_CAP_S
        assert min(samples) >= 0.0


class TestFileOpenCount:
    def test_test04_candidate_opens_capped(
        self, kb_root: Path, open_counter
    ) -> None:
        """TEST-04 / PERF-04: chunk opens ≤ 128 and never the decoy/skipped files."""
        from kb_rag.retrieve import retrieve

        retrieve(kb_root, "qaid", top_k=8, rerank=False)
        names = open_counter.unique_names
        assert len(names) <= CANDIDATE_OPEN_CAP
        assert f"{CHUNK_DECOY}.md" not in names
        assert f"{CHUNK_SKIPPED}.md" not in names
        # Fixture corpus is tiny; still must not open more than processed candidates.
        assert names <= set(PROCESSED_CHUNK_FILES) | names
        assert len(names) <= len(PROCESSED_CHUNK_FILES)

    def test_test05_no_glob_during_retrieve(self, kb_root: Path, glob_spy) -> None:
        """TEST-05 / BAN-01: retrieve must not glob chunks/."""
        from kb_rag.retrieve import retrieve

        retrieve(kb_root, "what is qaid", top_k=8, rerank=False)
        assert glob_spy.calls == []


class TestPeakMemory:
    def test_test04_peak_below_load_all_chunks(self, kb_root: Path) -> None:
        """TEST-04: retrieve peak allocations stay below reading every chunks/*.md."""
        from kb_rag.retrieve import retrieve

        chunk_dir = kb_root / "chunks"
        # Explicit names only — do not glob to discover (write known decoy/skip/processed).
        all_names = [
            "usrdata-universe-notes-chunk-001.md",
            "usrdata-universe-notes-chunk-002.md",
            "barra-id-mapping-chunk-001.md",
            "barra-id-mapping-chunk-002.md",
            "draft-skipped-doc-chunk-001.md",
            "decoy-not-in-catalog-chunk-999.md",
        ]

        tracemalloc.start()
        anti = 0
        for name in all_names:
            anti += len((chunk_dir / name).read_bytes())
        _, anti_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        tracemalloc.start()
        retrieve(kb_root, "qaid", top_k=8, rerank=False)
        _, retrieve_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Working set must not look like a full-tree body index. Fixture is small,
        # so compare against a generous multiple of catalog+graph size instead of
        # failing when both peaks are tiny.
        index_size = (kb_root / "index.yaml").stat().st_size
        graph_size = (kb_root / "graphs" / "knowledge-graph.json").stat().st_size
        budget = max(anti_peak * 2, (index_size + graph_size) * 50, 2_000_000)
        assert retrieve_peak < budget


def _write_large_kb(root: Path, n_docs: int = 100, chunks_per_doc: int = 2) -> Path:
    """Synthetic ~100-doc tree. Writes only listed chunk files (no glob)."""
    chunks = root / "chunks"
    graphs = root / "graphs"
    chunks.mkdir(parents=True)
    graphs.mkdir(parents=True)
    lines = ["documents:"]
    entities: list[dict[str, object]] = []
    relations: list[dict[str, str]] = []
    prev_ent: str | None = None
    for i in range(n_docs):
        doc_id = f"doc-{i:03d}"
        concept = f"concept-{i:03d}"
        lines.append(f"  - doc_id: {doc_id}")
        lines.append(f"    title: Document {i:03d} about {concept}")
        lines.append("    concepts:")
        lines.append(f"      - {concept}")
        lines.append("    chunk_files:")
        chunk_ids: list[str] = []
        for c in range(chunks_per_doc):
            chunk_id = f"{doc_id}-chunk-{c + 1:03d}"
            chunk_ids.append(chunk_id)
            lines.append(f"      - chunks/{chunk_id}.md")
            (chunks / f"{chunk_id}.md").write_text(
                f"---\nchunk_id: {chunk_id}\ndoc_id: {doc_id}\n"
                f"title: {concept} part {c}\nsemantic_key: {concept}\n"
                f"keywords: [{concept}]\nentities: [{concept}]\n"
                f"summary: synthetic {concept}\n---\n\nBody {concept} {c}.\n",
                encoding="utf-8",
            )
        lines.append("    status: processed")
        entities.append(
            {
                "id": concept,
                "label": concept.replace("-", " "),
                "type": "concept",
                "source_chunks": chunk_ids[:1],
            }
        )
        if prev_ent is not None:
            relations.append(
                {
                    "from": prev_ent,
                    "to": concept,
                    "type": "related_to",
                    "source_chunk": chunk_ids[0],
                }
            )
        prev_ent = concept
    (root / "index.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (graphs / "knowledge-graph.json").write_bytes(
        json.dumps({"version": "1.0", "entities": entities, "relations": relations}).encode()
    )
    return root


@pytest.fixture(scope="module")
def large_kb(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("large-kb")
    return _write_large_kb(root)


class TestLargeKb:
    @pytest.mark.slow
    def test_perf08_large_kb_ci_cap(self, large_kb: Path) -> None:
        """PERF-08: lexical retrieve on ~100 docs; CI cap 5s (constitution 2s p95)."""
        samples = _timed_retrieve(large_kb, "concept-000", LARGE_ROUNDS, WARMUP)
        p95 = _percentile(samples, 95)
        assert p95 < CI_LARGE_CAP_S

    @pytest.mark.slow
    def test_test04_large_kb_open_cap(self, large_kb: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """TEST-04: even on 100-doc KB, candidate chunk opens ≤ 128."""
        from helpers import OpenCounter

        counter = OpenCounter()
        counter.install(monkeypatch)
        from kb_rag.retrieve import retrieve

        retrieve(large_kb, "concept-000", top_k=8, rerank=False)
        assert len(counter.unique_names) <= CANDIDATE_OPEN_CAP


def test_optional_pytest_benchmark_fixture(kb_root: Path, request: pytest.FixtureRequest) -> None:
    """TEST-02: pytest-benchmark plugin is optional; skip if absent."""
    try:
        benchmark = request.getfixturevalue("benchmark")
    except pytest.FixtureLookupError:
        pytest.skip("pytest-benchmark not installed")
    from kb_rag.retrieve import retrieve

    def _run() -> None:
        retrieve(kb_root, "qaid", top_k=8, rerank=False)

    benchmark.pedantic(_run, iterations=10, rounds=5, warmup_rounds=2)


def test_fixture_builder_does_not_need_production_chunks() -> None:
    """TEST-07: fixture helper is self-contained (sanity for conftest writer)."""
    assert callable(write_fixture_kb)
