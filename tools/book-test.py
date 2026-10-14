#!/usr/bin/env python3
"""Unit tests for tools/book.py.

Covers the pure, deterministic helpers and validators in book.py — the
functions that do not require Ollama, the filesystem, or network access.

Run from the repo root:

    python -m unittest tools.book-test -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Make `book` importable regardless of how the test is invoked.
REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import book  # noqa: E402


class TestValidateBookname(unittest.TestCase):
    def test_valid_names(self):
        self.assertEqual(book.validate_bookname("mitali"), "mitali")
        self.assertEqual(book.validate_bookname("  wife  "), "wife")

    def test_rejects_blank(self):
        for bad in ("", "   ", ".", ".."):
            with self.assertRaises(ValueError):
                book.validate_bookname(bad)

    def test_rejects_path_and_special_chars(self):
        for bad in ("a/b", "a\\b", "a:b", 'a"b', "a*b", "a?b", "a<b", "a>b", "a|b"):
            with self.assertRaises(ValueError):
                book.validate_bookname(bad)


class TestResolveHelpers(unittest.TestCase):
    def test_resolve_form(self):
        self.assertEqual(book.resolve_form([None, "novel", "poetry"]), "novel")
        self.assertEqual(book.resolve_form([None, None]), "poetry")
        self.assertEqual(book.resolve_form([None, None], fallback="novel"), "novel")

    def test_resolve_count(self):
        self.assertEqual(book.resolve_count(["40", "novel"]), 40)
        self.assertEqual(book.resolve_count(["novel", None]), None)
        self.assertEqual(book.resolve_count([None, "abc"]), None)


class TestBacklogContentHelpers(unittest.TestCase):
    def test_read_seed_empty_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(book.read_seed(Path(tmp)), [])

    def test_read_seed_reads_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "seed.txt").write_text("one\n\ntwo\nthree\n", encoding="utf-8")
            self.assertEqual(book.read_seed(d), ["one", "two", "three"])

    def test_read_materials_empty_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(book.read_materials(Path(tmp)), "")

    def test_read_materials_concatenates(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "materials" / "sub").mkdir(parents=True)
            (d / "materials" / "a.md").write_text("alpha", encoding="utf-8")
            (d / "materials" / "sub" / "b.md").write_text("beta", encoding="utf-8")
            text = book.read_materials(d)
            self.assertIn("--- a.md ---", text)
            self.assertIn("alpha", text)
            self.assertIn("--- sub/b.md ---", text)
            self.assertIn("beta", text)

    def test_default_gist(self):
        self.assertIn("mitali", book.default_gist("mitali", "poetry"))
        self.assertIn("mitali", book.default_gist("mitali", "novel"))

    def test_make_title(self):
        self.assertEqual(book.make_title("mitali", "poetry"), "mitali: এর কবিতা")
        self.assertEqual(book.make_title("mitali", "novel"), "mitali: এর কাহিনি")


class TestMakeChapters(unittest.TestCase):
    def test_uses_seed_topics(self):
        chaps = book.make_chapters("m", "poetry", ["a", "b", "c"])
        self.assertEqual(len(chaps), 3)
        self.assertEqual([c["chapter_title"] for c in chaps], ["a", "b", "c"])
        self.assertEqual([c["name"] for c in chaps], ["1", "2", "3"])
        self.assertEqual([c["chapter_index"] for c in chaps], [1, 2, 3])

    def test_count_override_and_word_target(self):
        chaps = book.make_chapters("m", "poetry", [], chapter_count=5)
        self.assertEqual(len(chaps), 5)
        self.assertTrue(all(c["word_target"] == 500 for c in chaps))

        novel_chaps = book.make_chapters("m", "novel", [], chapter_count=2)
        self.assertTrue(all(c["word_target"] == 4500 for c in novel_chaps))

    def test_pads_when_seed_shorter(self):
        chaps = book.make_chapters("m", "poetry", ["only"], chapter_count=4)
        self.assertEqual(len(chaps), 4)
        self.assertEqual(chaps[0]["chapter_title"], "only")


class TestMakeBookJson(unittest.TestCase):
    def test_poetry_shape_and_filter_chain(self):
        chaps = book.make_chapters("m", "poetry", ["a"], chapter_count=1)
        plan = book.make_book_json("m", "poetry", "gist", chaps, "2026-01-01")
        self.assertEqual(plan["book_name"], "m")
        self.assertEqual(plan["form"], "poetry")
        self.assertEqual(plan["chapter_count"], 1)
        self.assertEqual(plan["word_target"], 500)
        self.assertEqual(plan["filter_chain"], book.FILTER_CHAIN_POETRY)

    def test_novel_filter_chain(self):
        chaps = book.make_chapters("m", "novel", ["a"], chapter_count=1)
        plan = book.make_book_json("m", "novel", "gist", chaps, "2026-01-01")
        self.assertEqual(plan["filter_chain"], book.FILTER_CHAIN_NOVEL)
        self.assertEqual(plan["word_target"], 4500)


class TestMakeEpic(unittest.TestCase):
    def test_contains_sections(self):
        chaps = book.make_chapters("m", "poetry", ["a", "b"], chapter_count=2)
        epic = book.make_epic("m", "poetry", "gist", chaps, "2026-01-01")
        self.assertIn("m", epic)
        self.assertIn("## পর্বের বিন্যাস", epic)
        self.assertIn("### 1. a", epic)
        self.assertIn("### 2. b", epic)


class TestExtractJson(unittest.TestCase):
    def test_bare_object(self):
        self.assertEqual(book.extract_json('{"a": 1}'), {"a": 1})

    def test_bare_list(self):
        self.assertEqual(book.extract_json("[1, 2]", expect_list=True), [1, 2])

    def test_fenced_json(self):
        data = book.extract_json("```json\n{\"a\": 1}\n```")
        self.assertEqual(data, {"a": 1})

    def test_unwraps_chapters_key(self):
        data = book.extract_json('{"chapters": [{"n": 1}]}', expect_list=True)
        self.assertEqual(data, [{"n": 1}])

    def test_rejects_non_object(self):
        with self.assertRaises(ValueError):
            book.extract_json("[1, 2]")

    def test_rejects_non_list(self):
        with self.assertRaises(ValueError):
            book.extract_json('{"a": 1}', expect_list=True)


class TestValidateLayout(unittest.TestCase):
    def _base(self):
        return {
            "book_name": "m",
            "book_long_title": "M",
            "chapter_count": 1,
            "form": "poetry",
            "filter_chain": ["workshop"],
            "chapters": [
                {
                    "chapter_index": 1,
                    "name": "1",
                    "chapter_title": "T",
                    "chapter_summary": "word " * 160,
                }
            ],
        }

    def test_valid(self):
        base = self._base()
        self.assertEqual(book.validate_layout(base, "m", "poetry"), base)

    def test_missing_field(self):
        data = self._base()
        del data["book_long_title"]
        with self.assertRaises(ValueError):
            book.validate_layout(data, "m", "poetry")

    def test_bookname_mismatch(self):
        with self.assertRaises(ValueError):
            book.validate_layout(self._base(), "other", "poetry")

    def test_form_mismatch(self):
        with self.assertRaises(ValueError):
            book.validate_layout(self._base(), "m", "novel")

    def test_chapter_count_mismatch(self):
        data = self._base()
        data["chapter_count"] = 99
        with self.assertRaises(ValueError):
            book.validate_layout(data, "m", "poetry")

    def test_underwritten_summary(self):
        data = self._base()
        data["chapters"][0]["chapter_summary"] = "too short"
        with self.assertRaises(ValueError):
            book.validate_layout(data, "m", "poetry")


class TestSummaryHelpers(unittest.TestCase):
    def test_word_target(self):
        self.assertEqual(book._summary_word_target("one two three"), 3)
        self.assertEqual(book._summary_word_target(None), 1)  # str(None) -> "None"

    def test_short_summary_indices(self):
        chapters = {
            1: {"chapter_summary": "word " * 200},
            2: {"chapter_summary": "short"},
        }
        self.assertEqual(book._short_summary_indices(chapters, 2), [2])

    def test_incomplete_chapters(self):
        chapters = {1: {"chapter_summary": "word " * 200}}
        self.assertEqual(book._incomplete_chapters(chapters, 3), [2, 3])


if __name__ == "__main__":
    unittest.main(verbosity=2)
