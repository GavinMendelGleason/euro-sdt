"""Deterministic sentence tokenisation and normalised text mapping.

The v1 pipeline had two tokenisers and a broken regex fallback. This module is
the only tokeniser used by v2: sentence boundaries are computed from character
offsets, and normalisation keeps a map back to original offsets so a quote can
always be resolved to a character span and a sentence span.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

# Abbreviations that must not end a sentence. Kept deliberately small: a
# wrong boundary only widens a sentence span, it does not lose evidence.
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sir", "dame", "jr", "sr", "st",
    "vs", "etc", "no", "nos", "art", "arts", "p", "pp", "cf", "al",
    "inc", "ltd", "co", "corp", "plc", "gmbh", "ag", "sa", "nv", "bv",
    "e.g", "i.e", "u.s", "u.k", "e.u", "eu", "un", "nato",
}

ENTITY_RE = re.compile(r"&(?:#(\d+)|#x([0-9a-fA-F]+)|([a-zA-Z][a-zA-Z0-9]+));")
BOUNDARY_RE = re.compile(r'[.!?]+["\')\]]*\s+')
PARA_RE = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class SentenceSpan:
    ordinal: int
    char_start: int
    char_end: int
    text: str


def _decode_entity(match: re.Match[str]) -> str:
    dec = match.group(1)
    hexdec = match.group(2)
    name = match.group(3)
    if dec:
        try:
            return chr(int(dec))
        except ValueError:
            return match.group(0)
    if hexdec:
        try:
            return chr(int(hexdec, 16))
        except ValueError:
            return match.group(0)
    if name:
        return html.unescape(match.group(0))
    return match.group(0)


def normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Return (normalised_text, original_offsets).

    original_offsets[i] is the index in ``text`` of the character that produced
    normalised character i. Whitespace collapses to one space; HTML entities are
    decoded. Case is folded.
    """
    out: list[str] = []
    offsets: list[int] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "&":
            m = ENTITY_RE.match(text, i)
            if m:
                decoded = _decode_entity(m)
                for d in decoded:
                    if d.isspace():
                        if out and out[-1] != " ":
                            out.append(" ")
                            offsets.append(i)
                    else:
                        out.append(d.lower())
                        offsets.append(i)
                i = m.end()
                continue
        if ch.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                offsets.append(i)
        else:
            out.append(ch.lower())
            offsets.append(i)
        i += 1
    # Trim leading/trailing spaces while keeping the map aligned.
    while out and out[0] == " ":
        out.pop(0)
        offsets.pop(0)
    while out and out[-1] == " ":
        out.pop()
        offsets.pop()
    return "".join(out), offsets


def normalize_text(text: str) -> str:
    return normalize_with_map(text)[0]


def _split_points(text: str) -> list[int]:
    """Return character positions at which a new sentence may start."""
    points: set[int] = {0}
    for m in BOUNDARY_RE.finditer(text):
        prefix = text[max(0, m.start() - 24):m.start()]
        words = re.findall(r"[A-Za-z][A-Za-z.]*", prefix)
        if words:
            last = words[-1].lower().rstrip(".")
            if last in ABBREVIATIONS:
                continue
        nxt = text[m.end():m.end() + 1]
        if not nxt:
            continue
        if not (nxt.isupper() or nxt.isdigit() or nxt in '"“\'([«'):
            continue
        points.add(m.end())
    for m in PARA_RE.finditer(text):
        points.add(m.end())
    ordered = sorted(p for p in points if 0 < p < len(text))
    return ordered


def sentence_spans(text: str, min_chars: int = 20, max_chars: int = 2000) -> list[SentenceSpan]:
    """Split text into sentence spans with exact original offsets.

    Very short fragments are merged into the following sentence. Very long
    unpunctuated blocks are split at paragraph/semicolon boundaries so a single
    row never hides multiple claims.
    """
    if not text.strip():
        return []
    starts = _split_points(text)
    bounds = [0] + starts + [len(text)]
    raw: list[tuple[int, int]] = []
    for a, b in zip(bounds, bounds[1:]):
        if b <= a:
            continue
        segment = text[a:b]
        if len(segment.strip()) == 0:
            continue
        if len(segment) > max_chars:
            pieces = re.split(r"(?<=[;:])\s+|\n\s*\n", segment)
            cursor = a
            for piece in pieces:
                if not piece:
                    continue
                p_end = cursor + len(piece)
                if piece.strip():
                    raw.append((cursor, p_end))
                cursor = p_end
        else:
            raw.append((a, b))

    merged: list[tuple[int, int]] = []
    for a, b in raw:
        if merged and len(text[merged[-1][0]:merged[-1][1]].strip()) < min_chars:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    spans: list[SentenceSpan] = []
    for ordinal, (a, b) in enumerate(merged):
        chunk = text[a:b]
        left = a + (len(chunk) - len(chunk.lstrip()))
        right = b - (len(chunk) - len(chunk.rstrip()))
        spans.append(SentenceSpan(ordinal, left, right, text[left:right]))
    return spans
