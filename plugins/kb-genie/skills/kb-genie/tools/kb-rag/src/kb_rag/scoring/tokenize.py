from __future__ import annotations

import re
import sys

# OPT-04: compile once at import; never inside tokenize().
TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> tuple[str, ...]:
    """Casefold, emit alnum tokens, plus hyphen-stripped aliases (qa-id → qaid)."""
    folded = text.casefold()
    if not folded:
        return ()
    out: list[str] = []
    n = len(folded)
    i = 0
    intern = sys.intern
    match = TOKEN_RE.match
    while i < n:
        m = match(folded, i)
        if m is None:
            i += 1
            continue
        group: list[str] = []
        while True:
            m = match(folded, i)
            if m is None:
                break
            tok = intern(m.group(0))
            out.append(tok)
            group.append(tok)
            i = m.end()
            if i < n and folded[i] == "-" and i + 1 < n and match(folded, i + 1) is not None:
                i += 1
                continue
            break
        if len(group) >= 2:
            out.append(intern("".join(group)))
    return tuple(out)
