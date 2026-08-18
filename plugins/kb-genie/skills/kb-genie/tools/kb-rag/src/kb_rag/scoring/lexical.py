from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence

from kb_rag.scoring.tokenize import tokenize

FIELD_WEIGHTS: dict[str, int] = {
    "semantic_key": 8,
    "title": 6,
    "keywords": 4,
    "potential_questions": 4,
    "entities": 3,
    "concepts": 3,
    "summary": 2,
    "body": 1,
}

_PHRASE_BONUS = 2.0
_KEBAB_BONUS = 1.0


def _as_text(value: str | Sequence[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return " ".join(str(item) for item in value)


def score_fields(
    query_tokens: Sequence[str],
    fields: Mapping[str, str | Sequence[str] | None],
    *,
    query_text: str | None = None,
) -> float:
    """Additive field-weighted term score + phrase bonus + kebab-id bonus."""
    weights = FIELD_WEIGHTS  # OPT-06: bind hot locals
    qtoks = query_tokens
    intern = sys.intern
    phrase = (query_text if query_text is not None else " ".join(qtoks)).casefold()
    q_stripped = {intern(tok) for tok in qtoks}
    total = 0.0
    for name, raw in fields.items():
        weight = weights.get(name)
        if weight is None:
            continue
        text = _as_text(raw)
        if not text:
            continue
        field_tokens = {intern(tok) for tok in tokenize(text)}
        for tok in qtoks:
            if tok in field_tokens:
                total += weight
        lower = text.casefold()
        if phrase and phrase in lower:
            total += _PHRASE_BONUS
        # kebab-id: hyphen-stripped query token present in hyphen-stripped field
        stripped_field = intern(lower.replace("-", "")) if "-" in lower else lower
        for tok in q_stripped:
            if tok and tok in field_tokens:
                continue
            if tok and tok in stripped_field:
                total += _KEBAB_BONUS
                break
    return total
