"""Lexical field-weight ordering tests (FR-08 / ALGO-05)."""

from __future__ import annotations

from kb_rag.scoring.lexical import FIELD_WEIGHTS, score_fields
from kb_rag.scoring.tokenize import tokenize


class TestFieldWeights:
    def test_fr08_constitution_weights(self) -> None:
        """FR-08: FIELD_WEIGHTS match constitution ALGO-05."""
        assert FIELD_WEIGHTS["semantic_key"] == 8
        assert FIELD_WEIGHTS["title"] == 6
        assert FIELD_WEIGHTS["keywords"] == 4
        assert FIELD_WEIGHTS["potential_questions"] == 4
        assert FIELD_WEIGHTS["entities"] == 3
        assert FIELD_WEIGHTS["concepts"] == 3
        assert FIELD_WEIGHTS["summary"] == 2
        assert FIELD_WEIGHTS["body"] == 1


class TestFieldWeightOrdering:
    def _score_only(self, field: str, text: str) -> float:
        tokens = tokenize("qaid")
        fields = dict.fromkeys(FIELD_WEIGHTS, None)
        fields[field] = text
        return score_fields(tokens, fields, query_text="qaid")

    def test_fr08_semantic_key_outranks_title(self) -> None:
        """FR-08: semantic_key weight > title for the same token."""
        assert self._score_only("semantic_key", "qaid") > self._score_only("title", "qaid")

    def test_fr08_title_outranks_keywords(self) -> None:
        """FR-08: title weight > keywords for the same token."""
        assert self._score_only("title", "qaid") > self._score_only("keywords", "qaid")

    def test_fr08_keywords_equals_potential_questions(self) -> None:
        """FR-08: keywords and potential_questions share weight 4."""
        assert self._score_only("keywords", "qaid") == self._score_only(
            "potential_questions", "qaid"
        )

    def test_fr08_keywords_outranks_entities(self) -> None:
        """FR-08: keywords weight > entities / concepts."""
        assert self._score_only("keywords", "qaid") > self._score_only("entities", "qaid")
        assert self._score_only("entities", "qaid") == self._score_only("concepts", "qaid")

    def test_fr08_entities_outranks_summary(self) -> None:
        """FR-08: entities weight > summary."""
        assert self._score_only("entities", "qaid") > self._score_only("summary", "qaid")

    def test_fr08_summary_outranks_body(self) -> None:
        """FR-08: summary weight > body."""
        assert self._score_only("summary", "qaid") > self._score_only("body", "qaid")

    def test_fr08_phrase_bonus_increases_score(self) -> None:
        """FR-08: exact phrase bonus on lowercased field increases score."""
        tokens = tokenize("what is qaid")
        fields = {"title": "what is qaid in usrdata"}
        with_phrase = score_fields(tokens, fields, query_text="what is qaid")
        fields_no = {"title": "qaid appears without the full phrase"}
        without = score_fields(tokens, fields_no, query_text="what is qaid")
        assert with_phrase > without

    def test_fr08_kebab_bonus_on_hyphenated_field(self) -> None:
        """FR-08: kebab-id bonus — query qa-id scores a field containing qaid."""
        tokens = tokenize("qa-id")
        hit = score_fields(tokens, {"semantic_key": "qaid"}, query_text="qa-id")
        miss = score_fields(tokens, {"semantic_key": "unrelated"}, query_text="qa-id")
        assert hit > miss
