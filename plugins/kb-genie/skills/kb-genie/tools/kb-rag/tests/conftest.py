"""Pytest fixtures: tiny kb-genie tree under tmp_path (no chunks/ glob)."""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers import (
    FixtureKB,
    GlobSpy,
    OpenCounter,
    write_fixture_kb,
)

# Re-export helpers used by tests that import conftest historically.
from helpers import (  # noqa: F401
    CHUNK_BARRA_1,
    CHUNK_BARRA_2,
    CHUNK_DECOY,
    CHUNK_NOTES_1,
    CHUNK_NOTES_2,
    CHUNK_SKIPPED,
    CONCEPT_QAID,
    DECOY_TOKEN,
    DOC_BARRA,
    DOC_NOTES,
    DOC_SKIPPED,
    ENTITY_BARRA,
    ENTITY_DS,
    ENTITY_QAID,
    PROCESSED_CHUNK_FILES,
    SKIPPED_TOKEN,
    block_sentence_transformers,
    collect_strings,
    neighbor_ids_from_payload,
    run_cli,
)


@pytest.fixture
def fixture_kb(tmp_path: Path) -> FixtureKB:
    return write_fixture_kb(tmp_path / "kb")


@pytest.fixture
def kb_root(fixture_kb: FixtureKB) -> Path:
    return fixture_kb.root


@pytest.fixture
def open_counter(monkeypatch: pytest.MonkeyPatch) -> OpenCounter:
    counter = OpenCounter()
    counter.install(monkeypatch)
    return counter


@pytest.fixture
def glob_spy(monkeypatch: pytest.MonkeyPatch) -> GlobSpy:
    spy = GlobSpy()
    spy.install(monkeypatch)
    return spy


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: larger synthetic KB")
