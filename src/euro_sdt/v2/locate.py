"""Deterministic quote location.

Nothing here calls an LLM. A quote must be found in the cited source text; if it
is not, the evidence is rejected rather than assigned a guessed index.
"""

from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

from .tokenizer import SentenceSpan, normalize_text, normalize_with_map

PREFIX_LENGTHS = (240, 200, 160, 120, 90, 60, 40)
STOP_TOKENS = {
    "the", "of", "and", "for", "on", "in", "at", "to", "a", "an", "de", "la",
    "le", "des", "du", "der", "die", "das", "van", "von", "den", "el", "y",
    "european", "europe", "international", "national", "institute", "council",
    "centre", "center", "foundation", "association", "organisation",
    "organization", "group", "university", "committee", "commission", "board",
    "programme", "program", "policy", "research", "studies", "school",
    "college", "department", "agency", "office", "bank", "company", "corp",
    "corporation", "limited", "ltd", "inc", "sa", "se", "ag", "plc", "gmbh",
    "societe", "society", "federation", "union", "party", "alliance",
}


@dataclass(frozen=True)
class QuoteLocation:
    status: str                  # located | quote_not_found | empty_quote
    char_start: int | None = None
    char_end: int | None = None
    sentence_start_ordinal: int | None = None
    sentence_end_ordinal: int | None = None
    matched_chars: int = 0
    matched_prefix: bool = False


class DocumentIndex:
    """Normalised text plus sentence offsets for one document."""

    def __init__(self, text: str, sentences: list[SentenceSpan]):
        self.text = text
        self.sentences = sentences
        self.norm, self.offsets = normalize_with_map(text)
        self._starts = [s.char_start for s in sentences]

    def _sentence_at(self, char_pos: int) -> int:
        idx = bisect.bisect_right(self._starts, char_pos) - 1
        return max(0, min(idx, len(self.sentences) - 1))

    def sentence_for_ordinal(self, ordinal: int | None) -> SentenceSpan | None:
        if ordinal is None:
            return None
        if 0 <= ordinal < len(self.sentences):
            return self.sentences[ordinal]
        return None

    def locate(
        self,
        quote: str,
        hint_ordinal: int | None = None,
        subject_aliases: tuple[str, ...] = (),
    ) -> QuoteLocation:
        if not quote or not quote.strip():
            return QuoteLocation("empty_quote")
        qnorm = normalize_text(quote)
        if len(qnorm) < 8:
            return QuoteLocation("quote_not_found", matched_chars=len(qnorm))

        candidates: list[tuple[int, int, int, int]] = []  # (score, orig_start, orig_end, norm_idx)
        hint_char = None
        if hint_ordinal is not None and 0 <= hint_ordinal < len(self.sentences):
            hint_char = self.sentences[hint_ordinal].char_start

        for length in PREFIX_LENGTHS:
            if length > len(qnorm):
                if length != PREFIX_LENGTHS[0]:
                    continue
                prefix = qnorm
            else:
                prefix = qnorm[:length]
            if len(prefix) < 8:
                continue
            start = 0
            found = False
            while True:
                idx = self.norm.find(prefix, start)
                if idx < 0:
                    break
                found = True
                end = idx + len(prefix)
                orig_start = self.offsets[idx]
                orig_end = self.offsets[end - 1] + 1
                score = 0
                if hint_char is not None:
                    score -= abs(orig_start - hint_char) // 100
                if subject_aliases:
                    window = self.norm[max(0, idx - 500):min(len(self.norm), end + 500)]
                    if any(alias and alias in window for alias in subject_aliases):
                        score += 20
                candidates.append((score, orig_start, orig_end, idx))
                start = idx + 1
            if found:
                break

        if not candidates:
            return QuoteLocation("quote_not_found", matched_chars=0)
        candidates.sort(key=lambda item: (-item[0], item[1]))
        _, start, end, norm_idx = candidates[0]
        # Prefer the full normalised quote when it also occurs at that position.
        if self.norm.startswith(qnorm, norm_idx):
            end = self.offsets[norm_idx + len(qnorm) - 1] + 1
        start_sent = self._sentence_at(start)
        end_sent = self._sentence_at(max(start, end - 1))
        return QuoteLocation(
            "located",
            start,
            end,
            start_sent,
            end_sent,
            matched_chars=end - start,
            matched_prefix=(end - start) < len(qnorm),
        )

    def span_text(self, start_ordinal: int, end_ordinal: int, pad: int = 0) -> str:
        a = max(0, start_ordinal - pad)
        b = min(len(self.sentences) - 1, end_ordinal + pad)
        if not self.sentences:
            return ""
        return self.text[self.sentences[a].char_start:self.sentences[b].char_end]


def tokens_for_alias(alias: str) -> tuple[str, ...]:
    norm = normalize_text(alias)
    tokens = [t for t in re.findall(r"[a-z0-9][a-z0-9&.'-]*", norm)]
    return tuple(t for t in tokens if len(t) >= 3 and t not in STOP_TOKENS)


def alias_in_text(text: str, aliases: tuple[str, ...]) -> bool:
    """Match an entity by full alias, distinctive token, or acronym."""
    if not aliases:
        return False
    norm = normalize_text(text)
    words = set(re.findall(r"[a-z0-9][a-z0-9&.'-]*", norm))
    for alias in aliases:
        a = normalize_text(alias)
        if not a:
            continue
        if a in norm:
            return True
        toks = tokens_for_alias(alias)
        if toks and all(t in words for t in toks):
            return True
        # acronym, e.g. "European Council on Foreign Relations" -> ecfr
        if len(a.split()) >= 3:
            initials = "".join(w[0] for w in a.split() if w)
            if len(initials) >= 3 and initials in words:
                return True
    return False
