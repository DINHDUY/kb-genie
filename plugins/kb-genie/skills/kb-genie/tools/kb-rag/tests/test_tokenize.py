"""Unit tests for kb_rag.scoring.tokenize (FR-14)."""

from __future__ import annotations

import inspect
import re

from kb_rag.scoring.tokenize import TOKEN_RE, tokenize


class TestTokenizeShortTokens:
    def test_fr14_keeps_short_token_qaid(self) -> None:
        """FR-14: short tokens like qaid are kept (not dropped as stopwords)."""
        tokens = tokenize("qaid")
        assert "qaid" in tokens

    def test_fr14_casefold(self) -> None:
        """FR-14: tokenize uses casefold (QAID → qaid)."""
        tokens = tokenize("QAID")
        assert "qaid" in tokens


class TestKebabAliases:
    def test_fr14_qa_id_alias_to_qaid(self) -> None:
        """FR-14 / EDGE-09: kebab-id aliases qa-id ↔ qaid."""
        tokens = tokenize("qa-id")
        assert "qa" in tokens
        assert "id" in tokens
        assert "qaid" in tokens

    def test_fr14_qaid_matches_hyphenated_query(self) -> None:
        """FR-14: tokenize('qaid') and tokenize('qa-id') share the qaid token."""
        assert "qaid" in tokenize("qaid")
        assert "qaid" in tokenize("qa-id")

    def test_edge09_barra_id(self) -> None:
        """EDGE-09: barra-id emits barra, id, and hyphen-stripped barraid."""
        tokens = tokenize("barra-id")
        assert "barra" in tokens
        assert "id" in tokens
        assert "barraid" in tokens


class TestTokenReModuleLevel:
    def test_fr14_token_re_is_compiled_pattern(self) -> None:
        """FR-14: TOKEN_RE is a module-level compiled regex."""
        assert isinstance(TOKEN_RE, re.Pattern)
        assert TOKEN_RE.pattern == r"[a-z0-9]+"

    def test_fr14_tokenize_does_not_compile_regex(self) -> None:
        """FR-14: tokenize() source must not call re.compile."""
        source = inspect.getsource(tokenize)
        assert "re.compile" not in source

    def test_fr14_empty_string(self) -> None:
        """FR-14: empty input yields an empty token tuple."""
        assert tokenize("") == ()
        assert tokenize("   ") == ()
