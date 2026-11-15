#!/usr/bin/env python3
"""Shared chapter/segment target parser for the enrich/write/review engines.

A target is a comma-separated list of terms, where each term selects a chapter
(optionally a single segment) or a range of chapters/segments:

    all | *              every chapter (whole chapters)
    3                    chapter 3 (all of its segments)
    3.2                  chapter 3, segment 2 only
    3.2-3.5              chapter 3, segments 2 through 5
    3-5                  chapters 3 through 5 (all segments)
    3.2,4.1              mixed list of chapter/segment targets

``3.2`` is read as ``<chapter>.<segment>``. Segment indices are 1-based and are
only meaningful for poetry chapters (one standalone poem per segment); a bare
chapter number still means "the whole chapter, every segment".

``continue`` is deliberately NOT handled here — each engine has its own notion of
which chapter to resume (unwritten vs. written-but-unreviewed), so callers wrap
this parser with their local ``continue`` resolution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SegmentTarget:
    """One chapter/segment selection.

    ``segment`` is ``None`` when the whole chapter is selected; otherwise it is
    the 1-based segment index within ``chapter``.
    """

    chapter: int
    segment: int | None = None

    @property
    def chapter_name(self) -> str:
        return str(self.chapter)

    def __str__(self) -> str:
        return f"{self.chapter}.{self.segment}" if self.segment else str(self.chapter)


_SINGLE_RE = re.compile(r"([0-9]+)(?:\.([0-9]+))?")


def _parse_single(token: str) -> tuple[int, int | None]:
    match = _SINGLE_RE.fullmatch(token)
    if match is None:
        raise ValueError(f"Invalid target term {token!r}")
    return int(match.group(1)), (int(match.group(2)) if match.group(2) else None)


def parse_target_spec(value: str, chapters_root: Path | None = None) -> list[SegmentTarget]:
    """Parse a chapter/segment target spec into an ordered, de-duplicated list.

    ``chapters_root`` is required only for ``all``/``*`` (to discover the
    numbered chapter folders). Explicit numeric targets do not validate that a
    chapter folder exists — the caller's per-chapter function reports that.
    """
    text = (value or "").strip().lower()
    if text in {"all", "*"}:
        if chapters_root is None:
            raise ValueError("A chapters directory is required for all or '*'")
        chapters = sorted({
            int(folder.name)
            for folder in chapters_root.iterdir()
            if folder.is_dir() and folder.name.isdecimal() and int(folder.name) > 0
        })
        if not chapters:
            raise ValueError(f"No numbered chapters found in {chapters_root}")
        return [SegmentTarget(chapter) for chapter in chapters]

    targets: list[SegmentTarget] = []
    seen: set[tuple[int, int | None]] = set()

    def _add(target: SegmentTarget) -> None:
        key = (target.chapter, target.segment)
        if key not in seen:
            seen.add(key)
            targets.append(target)

    for term in text.split(","):
        term = term.strip()
        if not term:
            continue
        if "-" in term:
            parts = term.split("-", 1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                raise ValueError(f"Invalid range {term!r}")
            c1, s1 = _parse_single(parts[0].strip())
            c2, s2 = _parse_single(parts[1].strip())
            if s1 is None and s2 is None:
                if c1 < 1 or c2 < c1:
                    raise ValueError("Chapter ranges must be positive and ascending")
                for chapter in range(c1, c2 + 1):
                    _add(SegmentTarget(chapter, None))
            elif s1 is not None and s2 is not None and c1 == c2:
                if s1 < 1 or s2 < s1:
                    raise ValueError("Segment ranges must be positive and ascending")
                for segment in range(s1, s2 + 1):
                    _add(SegmentTarget(c1, segment))
            else:
                raise ValueError(
                    "Range endpoints must both be chapters (3-5) or both be "
                    "segments of one chapter (3.2-3.5)"
                )
        else:
            chapter, segment = _parse_single(term)
            if chapter < 1 or (segment is not None and segment < 1):
                raise ValueError("Chapter and segment numbers must be positive")
            _add(SegmentTarget(chapter, segment))

    if not targets:
        raise ValueError("Empty target spec")
    return targets


def chapter_numbers(specs: list[SegmentTarget]) -> list[int]:
    """Unique chapter numbers in first-seen order."""
    seen: set[int] = set()
    numbers: list[int] = []
    for spec in specs:
        if spec.chapter not in seen:
            seen.add(spec.chapter)
            numbers.append(spec.chapter)
    return numbers


def group_by_chapter(specs: list[SegmentTarget]) -> dict[int, set[int] | None]:
    """Group targets by chapter.

    ``None`` means "the whole chapter, every segment". A concrete ``set[int]``
    lists the selected 1-based segments. If a chapter appears both whole and by
    segment (e.g. ``3`` and ``3.2``), the whole-chapter selection wins.
    """
    grouped: dict[int, set[int] | None] = {}
    for spec in specs:
        if spec.chapter not in grouped:
            if spec.segment is None:
                grouped[spec.chapter] = None
            else:
                grouped[spec.chapter] = {spec.segment}
            continue
        current = grouped[spec.chapter]
        if spec.segment is None:
            # Whole chapter supersedes any earlier segment-only selection.
            grouped[spec.chapter] = None
        elif current is not None:
            current.add(spec.segment)
        # current is None → whole chapter already; keep None.
    return grouped


