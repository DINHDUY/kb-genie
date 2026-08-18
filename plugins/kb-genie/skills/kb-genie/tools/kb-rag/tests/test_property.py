"""Property-based tests for kb-rag tokenize determinism (FR-14)."""

from __future__ import annotations

import re

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st

from kb_rag.scoring.tokenize import TOKEN_RE, tokenize

ALNUM_TOKEN = re.compile(r"^[a-z0-9]+$")


@given(st.text(max_size=500))
@settings(max_examples=200)
def test_fr14_tokenize_deterministic(text: str) -> None:
    """FR-14: tokenize(x) is deterministic for all unicode strings."""
    assert tokenize(text) == tokenize(text)


@given(st.text(max_size=500))
@settings(max_examples=200)
def test_fr14_tokens_are_lowercase_alnum(text: str) -> None:
    """FR-14: every emitted token matches [a-z0-9]+ (TOKEN_RE)."""
    for token in tokenize(text):
        assert ALNUM_TOKEN.fullmatch(token)
        assert TOKEN_RE.fullmatch(token)


@given(st.text(alphabet=st.characters(whitelist_categories=("L", "N")), max_size=80))
@settings(max_examples=200)
def test_fr14_repeated_tokenize_stable_tuple(text: str) -> None:
    """FR-14: return type is a tuple and equal across three invocations."""
    a = tokenize(text)
    b = tokenize(text)
    c = tokenize(text)
    assert isinstance(a, tuple)
    assert a == b == c


@given(
    st.lists(
        st.from_regex(r"[A-Za-z0-9]{1,12}", fullmatch=True),
        min_size=1,
        max_size=6,
    )
)
@settings(max_examples=200)
def test_fr14_hyphen_join_emits_stripped_alias(parts: list[str]) -> None:
    """FR-14: hyphenated identifiers emit the hyphen-stripped alias."""
    if len(parts) < 2:
        return
    kebab = "-".join(parts)
    tokens = tokenize(kebab)
    stripped = "".join(p.casefold() for p in parts)
    # stripped may still contain only alphanumerics after casefold
    stripped_alnum = "".join(ch for ch in stripped if ch.isalnum())
    if stripped_alnum:
        assert stripped_alnum in tokens
