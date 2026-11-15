#!/usr/bin/env python3
"""Unit tests for tools/book.py.

Covers the pure, deterministic helpers and validators in book.py — the
functions that do not require Ollama, the filesystem, or network access.

Run from the repo root:

    python -m unittest tools.book-test -v
"""

from __future__ import annotations

import json
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
import config_report  # noqa: E402
import pipeline_readme  # noqa: E402
import publish  # noqa: E402
import quality  # noqa: E402
import review  # noqa: E402
import segment_target  # noqa: E402


class TestSegmentTargetParser(unittest.TestCase):
    def _specs(self, value):
        return [str(s) for s in segment_target.parse_target_spec(value)]

    def test_single_chapter(self):
        self.assertEqual(self._specs("3"), ["3"])

    def test_float_segment(self):
        self.assertEqual(self._specs("3.2"), ["3.2"])

    def test_segment_range(self):
        self.assertEqual(self._specs("3.2-3.5"), ["3.2", "3.3", "3.4", "3.5"])

    def test_chapter_range(self):
        self.assertEqual(self._specs("3-5"), ["3", "4", "5"])

    def test_mixed_list(self):
        self.assertEqual(self._specs("3.2,4.1,4.3"), ["3.2", "4.1", "4.3"])

    def test_dedupe(self):
        self.assertEqual(self._specs("3,3,3.2,3.2"), ["3", "3.2"])

    def test_reject_mixed_range(self):
        with self.assertRaises(ValueError):
            segment_target.parse_target_spec("3.2-5")

    def test_chapter_numbers(self):
        specs = segment_target.parse_target_spec("3.2,4.1,4.3")
        self.assertEqual(segment_target.chapter_numbers(specs), [3, 4])

    def test_group_by_chapter_segments(self):
        specs = segment_target.parse_target_spec("3.2,3.4,4.1")
        self.assertEqual(segment_target.group_by_chapter(specs), {3: {2, 4}, 4: {1}})

    def test_group_by_chapter_whole_wins(self):
        specs = segment_target.parse_target_spec("3,3.2,4")
        self.assertEqual(segment_target.group_by_chapter(specs), {3: None, 4: None})


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
        self.assertTrue(all("segment_count" not in c for c in novel_chaps))

    def test_pads_when_seed_shorter(self):
        chaps = book.make_chapters("m", "poetry", ["only"], chapter_count=4)
        self.assertEqual(len(chaps), 4)
        self.assertEqual(chaps[0]["chapter_title"], "only")
        self.assertTrue(all(c["segment_count"] == 8 for c in chaps))


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
                    "segment_count": 8,
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


class TestPipelineReadme(unittest.TestCase):
    def setUp(self):
        self.plan = {
            "book_name": "demo",
            "form": "poetry",
            "chapter_count": 2,
            "word_target": 500,
            "style": "pijush",
            "factory": "online",
            "filter_chain": ["workshop", "research"],
            "quality_chain": ["subject", "theme"],
        }

    def test_render_states_book_facts_and_ownership(self):
        text = pipeline_readme.render(
            "demo", form="poetry", chapter_count=2, word_target=500,
            filter_chain=["workshop", "research"], quality_chain=["subject", "theme"],
            style="pijush", factory="online", updated_date="2026-01-01T00:00:00Z",
        )
        self.assertIn("# Pipeline — demo", text)
        self.assertIn("`workshop` → `research`", text)
        self.assertIn("| `book.json` |", text)
        self.assertIn("`chapters/`", text)
        self.assertIn("publish", text)
        self.assertIn(pipeline_readme.MARKER, text)

    def test_write_creates_readme_with_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = Path(tmp)
            self.assertTrue(
                pipeline_readme.write_for_pipeline(
                    pipeline, "demo", self.plan, stamp="2026-01-01T00:00:00Z",
                    logger=lambda *_: None,
                )
            )
            text = (pipeline / "README.md").read_text(encoding="utf-8")
            self.assertIn(pipeline_readme.MARKER, text)
            self.assertIn("2026-01-01T00:00:00Z", text)

    def test_generated_readme_is_refreshed(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = Path(tmp)
            pipeline_readme.write_for_pipeline(
                pipeline, "demo", self.plan, stamp="2026-01-01T00:00:00Z",
                logger=lambda *_: None,
            )
            grown = dict(self.plan, chapter_count=3)
            self.assertTrue(
                pipeline_readme.write_for_pipeline(
                    pipeline, "demo", grown, stamp="2026-01-02T00:00:00Z",
                    logger=lambda *_: None,
                )
            )
            text = (pipeline / "README.md").read_text(encoding="utf-8")
            self.assertIn("2026-01-02T00:00:00Z", text)
            self.assertIn("| 3 |", text)

    def test_hand_written_readme_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = Path(tmp)
            (pipeline / "README.md").write_text("# My notes\n", encoding="utf-8")
            self.assertFalse(
                pipeline_readme.write_for_pipeline(
                    pipeline, "demo", self.plan, logger=lambda *_: None
                )
            )
            self.assertEqual(
                (pipeline / "README.md").read_text(encoding="utf-8"), "# My notes\n"
            )


class TestFilterChainReconciliation(unittest.TestCase):
    """A poetry book laid out with the novel option must still scaffold."""

    NOVEL_CHAIN = ["research", "seeds", "correctness", "theme", "syntax", "override", "quality"]
    POETRY_CHAIN = list(quality.POETRY_FILTER_CHAIN)

    def test_poetry_chain_names_accepts_objects_and_strings(self):
        self.assertEqual(quality.filter_chain_names(self.POETRY_CHAIN), self.POETRY_CHAIN)
        self.assertEqual(
            quality.filter_chain_names([{"sl": 1, "filter": "workshop"}, {"name": "research"}]),
            ["workshop", "research"],
        )
        self.assertEqual(quality.filter_chain_names(["", None, "workshop"]), ["workshop"])

    def test_novel_chain_is_reconciled_for_poetry(self):
        plan = {"form": "poetry", "filter_chain": self.NOVEL_CHAIN}
        self.assertEqual(quality.reconcile_filter_chain(plan), self.POETRY_CHAIN)
        self.assertEqual(quality.poetry_filter_chain(self.NOVEL_CHAIN), self.POETRY_CHAIN)

    def test_canonical_poetry_chain_is_preserved(self):
        plan = {"form": "poetry", "filter_chain": self.POETRY_CHAIN}
        self.assertEqual(quality.reconcile_filter_chain(plan), self.POETRY_CHAIN)

    def test_novel_plan_keeps_its_chain(self):
        plan = {"form": "novel", "filter_chain": self.NOVEL_CHAIN}
        self.assertEqual(quality.reconcile_filter_chain(plan), self.NOVEL_CHAIN)

    def test_extra_filters_survive_when_order_is_intact(self):
        chain = self.POETRY_CHAIN[:2] + ["extra"] + self.POETRY_CHAIN[2:]
        self.assertEqual(quality.poetry_filter_chain(chain), chain)

    def test_stamp_json_syncs_legacy_updated_at(self):
        document = {"created_at": "2026-01-01T00:00:00Z", "updated_at": "old"}
        quality.stamp_json(document, "scaffold", "2026-02-02T00:00:00Z")
        self.assertEqual(document["updated_by"], "scaffold")
        self.assertEqual(document["updated_date"], "2026-02-02T00:00:00Z")
        self.assertEqual(document["updated_at"], "2026-02-02T00:00:00Z")
        self.assertEqual(document["created_at"], "2026-01-01T00:00:00Z")


class TestPublishOutputStructure(unittest.TestCase):
    def test_publishes_editor_segments_in_pipeline_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = root / "workspaces" / "pipeline" / "demo"
            chapter = pipeline / "chapters" / "1"
            editor = chapter / "segments" / "1" / "editor" / "segment.md"
            writer = chapter / "segments" / "1" / "writer" / "segment.md"
            editor.parent.mkdir(parents=True)
            writer.parent.mkdir(parents=True)
            editor.write_text("Reviewed poem.\n", encoding="utf-8")
            writer.write_text("Unreviewed poem.\n", encoding="utf-8")
            (pipeline / "book.json").parent.mkdir(parents=True, exist_ok=True)
            (pipeline / "book.json").write_text(json.dumps({
                "book_long_title": "Demo Book",
                "chapters": [{"name": "1"}],
            }), encoding="utf-8")
            (chapter / "chapter.json").write_text(json.dumps({
                "chapter_title": "First Chapter",
                "segments": [{"segment_index": 1, "segment_title": "First Segment"}],
            }), encoding="utf-8")
            (pipeline / "progress.json").write_text('{"chapters": []}', encoding="utf-8")

            original_root = publish.ROOT
            publish.ROOT = str(root)
            try:
                version_dir = publish.publish("demo", draft=True)
            finally:
                publish.ROOT = original_root

            published_segment = (
                version_dir / "chapters" / "1" / "segments" / "1" / "editor" / "segment.md"
            )
            self.assertTrue(published_segment.is_file())
            self.assertIn("Reviewed poem.", published_segment.read_text(encoding="utf-8"))
            self.assertNotIn("Unreviewed poem.", published_segment.read_text(encoding="utf-8"))
            # Publish mirrors the published editor poem into latest/segment.md.
            latest_segment = (
                version_dir / "chapters" / "1" / "segments" / "1" / "latest" / "segment.md"
            )
            self.assertTrue(latest_segment.is_file())
            self.assertIn("Reviewed poem.", latest_segment.read_text(encoding="utf-8"))
            self.assertNotIn("Unreviewed poem.", latest_segment.read_text(encoding="utf-8"))
            # The pipeline's own segment latest/ is refreshed from editor too.
            pipeline_latest = (
                chapter / "segments" / "1" / "latest" / "segment.md"
            )
            self.assertTrue(pipeline_latest.is_file())
            self.assertIn("Reviewed poem.", pipeline_latest.read_text(encoding="utf-8"))
            self.assertTrue((version_dir / "chapters" / "1" / "chapter.md").is_file())
            self.assertTrue((version_dir / "book.md").is_file())
            for path in version_dir.rglob("*"):
                if path.suffix == ".md":
                    self.assertIn("**updated_by:** publish", path.read_text(encoding="utf-8"))
                elif path.suffix == ".json":
                    self.assertEqual(
                        json.loads(path.read_text(encoding="utf-8"))["updated_by"],
                        "publish",
                    )
            progress = json.loads((pipeline / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual(progress["updated_by"], "publish")

    def test_publish_carries_the_print_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = root / "workspaces" / "pipeline" / "demo"
            chapter = pipeline / "chapters" / "1"
            editor = chapter / "segments" / "1" / "editor" / "segment.md"
            editor.parent.mkdir(parents=True)
            editor.write_text("Reviewed poem.\n", encoding="utf-8")
            (pipeline / "book.json").write_text(json.dumps({
                "book_long_title": "Demo Book",
                "chapters": [{"name": "1"}],
            }), encoding="utf-8")
            (chapter / "chapter.json").write_text(json.dumps({
                "chapter_title": "First Chapter",
                "segments": [{"segment_index": 1, "segment_title": "First Segment"}],
            }), encoding="utf-8")
            (pipeline / "progress.json").write_text('{"chapters": []}', encoding="utf-8")
            profile = pipeline / "profile" / "publish" / "default" / "profile.json"
            blurb = profile.parent / "pages" / "blurb" / "blurb.rtf"
            blurb.parent.mkdir(parents=True)
            blurb.write_text("blurb\n", encoding="utf-8")
            profile.write_text(
                json.dumps({"version": 1, "name": "default",
                            "book": {"pages": [{"order": 1, "file_path": "pages/blurb/",
                                                "format": "rtf", "paths": []}]}}),
                encoding="utf-8",
            )

            original_root = publish.ROOT
            publish.ROOT = str(root)
            try:
                version_dir = publish.publish("demo", draft=True)
            finally:
                publish.ROOT = original_root

            copied = version_dir / "profile" / "publish" / "default"
            written = json.loads((copied / "profile.json").read_text(encoding="utf-8"))
            # The copy records the published version as the folder its content
            # comes from, so a profile read on its own finds its own book.
            self.assertEqual(
                written.pop("source"),
                {"book_name": "demo", "source_format": "published",
                 "source_path": "demo", "version": 1},
            )
            self.assertEqual(
                written,
                json.loads(profile.read_text(encoding="utf-8")),
            )
            self.assertEqual(
                (copied / "pages" / "blurb" / "blurb.rtf").read_text(encoding="utf-8"),
                "blurb\n",
            )

    def test_publish_prefers_latest_stage_over_editor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = root / "workspaces" / "pipeline" / "demo"
            chapter = pipeline / "chapters" / "1"
            segment = chapter / "segments" / "1"
            (segment / "editor").mkdir(parents=True)
            (segment / "latest").mkdir(parents=True)
            # latest/ holds the newer finalized text; editor/ holds an older copy.
            (segment / "editor" / "segment.md").write_text("Older editor poem.\n", encoding="utf-8")
            (segment / "latest" / "segment.md").write_text("Newest latest poem.\n", encoding="utf-8")
            (pipeline / "book.json").parent.mkdir(parents=True, exist_ok=True)
            (pipeline / "book.json").write_text(json.dumps({
                "book_long_title": "Demo Book",
                "chapters": [{"name": "1"}],
            }), encoding="utf-8")
            (chapter / "chapter.json").write_text(json.dumps({
                "chapter_title": "First Chapter",
                "segments": [{"segment_index": 1, "segment_title": "First Segment"}],
            }), encoding="utf-8")
            (pipeline / "progress.json").write_text('{"chapters": []}', encoding="utf-8")

            original_root = publish.ROOT
            publish.ROOT = str(root)
            try:
                version_dir = publish.publish("demo", draft=True)
            finally:
                publish.ROOT = original_root

            for stage in ("editor", "latest"):
                published = (
                    version_dir / "chapters" / "1" / "segments" / "1" / stage / "segment.md"
                )
                self.assertTrue(published.is_file(), f"missing {stage}")
                text = published.read_text(encoding="utf-8")
                self.assertIn("Newest latest poem.", text)
                self.assertNotIn("Older editor poem.", text)
            self.assertIn(
                "Newest latest poem.",
                (version_dir / "chapters" / "1" / "chapter.md").read_text(encoding="utf-8"),
            )

    def test_publish_falls_back_to_editor_when_latest_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = root / "workspaces" / "pipeline" / "demo"
            chapter = pipeline / "chapters" / "1"
            segment = chapter / "segments" / "1"
            (segment / "editor").mkdir(parents=True)
            (segment / "editor" / "segment.md").write_text("Editor only poem.\n", encoding="utf-8")
            (pipeline / "book.json").parent.mkdir(parents=True, exist_ok=True)
            (pipeline / "book.json").write_text(json.dumps({
                "book_long_title": "Demo Book",
                "chapters": [{"name": "1"}],
            }), encoding="utf-8")
            (chapter / "chapter.json").write_text(json.dumps({
                "chapter_title": "First Chapter",
                "segments": [{"segment_index": 1, "segment_title": "First Segment"}],
            }), encoding="utf-8")
            (pipeline / "progress.json").write_text('{"chapters": []}', encoding="utf-8")

            original_root = publish.ROOT
            publish.ROOT = str(root)
            try:
                version_dir = publish.publish("demo", draft=True)
            finally:
                publish.ROOT = original_root

            published = (
                version_dir / "chapters" / "1" / "segments" / "1" / "latest" / "segment.md"
            )
            self.assertTrue(published.is_file())
            self.assertIn("Editor only poem.", published.read_text(encoding="utf-8"))
            # The pipeline latest/ is refreshed from the fallback source.
            pipeline_latest = chapter / "segments" / "1" / "latest" / "segment.md"
            self.assertTrue(pipeline_latest.is_file())
            self.assertIn("Editor only poem.", pipeline_latest.read_text(encoding="utf-8"))

    def test_partial_selection_skips_unpublished_chapters_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = root / "workspaces" / "pipeline" / "demo"
            book = pipeline / "book.json"
            book.parent.mkdir(parents=True)
            book.write_text(json.dumps({
                "book_long_title": "Demo Book",
                "chapters": [{"name": "1"}, {"name": "2"}],
            }), encoding="utf-8")

            for name, has_editor in (("1", True), ("2", False)):
                chapter = pipeline / "chapters" / name
                chapter.mkdir(parents=True)
                (chapter / "chapter.json").write_text(json.dumps({
                    "chapter_title": f"Chapter {name}",
                    "segments": [{"segment_index": 1, "segment_title": "Segment"}],
                }), encoding="utf-8")
                if has_editor:
                    editor = chapter / "segments" / "1" / "editor" / "segment.md"
                    editor.parent.mkdir(parents=True)
                    editor.write_text("Reviewed poem.\n", encoding="utf-8")
                else:
                    # A planned segment with no editor-stage poem gets skipped.
                    (chapter / "segments" / "1").mkdir(parents=True)

            (pipeline / "progress.json").write_text(json.dumps({
                "chapters": [
                    {"chapter_number": 1, "published": False},
                    {"chapter_number": 2, "published": False},
                ],
            }), encoding="utf-8")

            original_root = publish.ROOT
            publish.ROOT = str(root)
            try:
                version_dir = publish.publish("demo", draft=True)
            finally:
                publish.ROOT = original_root

            progress = json.loads((pipeline / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual(progress["updated_by"], "publish")
            rows = {str(r["chapter_number"]): r for r in progress["chapters"]}
            self.assertIn("published_sha256", rows["1"])
            self.assertNotIn("published_sha256", rows["2"])
            # Only the publishable chapter is present in the output.
            self.assertTrue(
                (version_dir / "chapters" / "1" / "segments" / "1" / "editor" / "segment.md").is_file()
            )
            self.assertFalse((version_dir / "chapters" / "2").exists())


class TestReviewArchivesToCanonicalVersionFolder(unittest.TestCase):
    def test_editor_copy_archives_into_segment_version_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            chapter_dir = Path(tmp) / "chapters" / "1"
            editor = chapter_dir / "segments" / "1" / "editor" / "segment.md"
            editor.parent.mkdir(parents=True)
            editor.write_text("previous reviewed poem\n", encoding="utf-8")

            written = review._write_editor_segment(chapter_dir, 1, "new reviewed poem")

            self.assertEqual(written, editor)
            self.assertEqual(
                editor.read_text(encoding="utf-8"), "new reviewed poem\n"
            )
            # Archive lands in the canonical segment version/ folder, not editor/version/.
            version_dir = chapter_dir / "segments" / "1" / "version"
            archived = version_dir / "segment_v1.md"
            self.assertTrue(archived.is_file())
            self.assertEqual(
                archived.read_text(encoding="utf-8"), "previous reviewed poem\n"
            )
            self.assertFalse(
                (chapter_dir / "segments" / "1" / "editor" / "version").exists()
            )
            # The finalized poem is mirrored into latest/segment.md.
            latest = chapter_dir / "segments" / "1" / "latest" / "segment.md"
            self.assertTrue(latest.is_file())
            self.assertEqual(
                latest.read_text(encoding="utf-8"), "new reviewed poem\n"
            )


class TestReviewCleanup(unittest.TestCase):
    def test_removes_summary_section_to_end_of_file(self):
        text = "## নদীর শরীর\nকবিতার প্রথম লাইন।\n\n## সারাংশঃ\nএই অংশ বাদ যাবে।\n"
        cleaned, summary_removed = review.strip_summary_section(text)
        self.assertTrue(summary_removed)
        self.assertIn("কবিতার প্রথম লাইন।", cleaned)
        self.assertNotIn("সারাংশ", cleaned)
        self.assertNotIn("এই অংশ বাদ যাবে", cleaned)

    def test_removes_summary_heading_variants(self):
        for heading in ("## সারাংশ", "## সারাংশঃ", "## Summary", "### সারাংশঃ"):
            text = f"কবিতা লাইন।\n\n{heading}\nসারাংশের লেখা।\n"
            cleaned, removed = review.strip_summary_section(text)
            self.assertTrue(removed, heading)
            self.assertNotIn("সারাংশের লেখা", cleaned, heading)

    def test_summary_removal_keeps_following_section(self):
        text = "## title\npoem\n\n## সারাংশ\nsummary text\n\n## next\nkept text\n"
        cleaned, removed = review.strip_summary_section(text)
        self.assertTrue(removed)
        self.assertNotIn("summary text", cleaned)
        self.assertIn("kept text", cleaned)

    def test_strips_non_target_script_words(self):
        text = "মাটির স্বাদ Turning Point এবং paradox ও कुछ हिंदी। শেষ।"
        cleaned, removed = review.strip_non_target_scripts(text, "bengali")
        self.assertIn("মাটির স্বাদ", cleaned)
        self.assertIn("শেষ।", cleaned)
        for foreign in ("Turning", "Point", "paradox", "कुछ", "हिंदी"):
            self.assertNotIn(foreign, cleaned)
        self.assertIn("Turning", removed)

    def test_keeps_target_script_digits_and_punctuation(self):
        text = "গোপালের নৌকা ভাসে। সে ১০টি মাছ ধরল।"
        cleaned, removed = review.strip_non_target_scripts(text, "bengali")
        self.assertEqual(cleaned, text)
        self.assertEqual(removed, [])

    def test_unmapped_script_is_a_no_op(self):
        text = "Some English with বাংলা mixed."
        cleaned, removed = review.strip_non_target_scripts(text, None)
        self.assertEqual(cleaned, text)
        self.assertEqual(removed, [])

    def test_clean_segment_text_is_idempotent(self):
        text = (
            "## নদীর শরীর\nকবিতার লাইন। Turning Point\n\n## সারাংশঃ\nবাদ যাবে।\n"
        )
        once, frags, summary, titles = review.clean_segment_text(text, "bengali")
        twice, frags2, summary2, titles2 = review.clean_segment_text(once, "bengali")
        self.assertTrue(summary)
        self.assertTrue(frags)
        self.assertEqual(titles, 1)
        self.assertEqual(twice, once)
        self.assertEqual(frags2, [])
        self.assertFalse(summary2)
        self.assertEqual(titles2, 0)

    def test_removes_single_line_title_heading(self):
        text = "## প্রাসাদের প্রথম আহ্বান\nপ্রথম লাইন।\nদ্বিতীয় লাইন।\n"
        cleaned, frags, summary, titles = review.clean_segment_text(text, "bengali")
        self.assertEqual(titles, 1)
        self.assertNotIn("প্রাসাদের প্রথম আহ্বান", cleaned)
        self.assertIn("প্রথম লাইন।", cleaned)
        self.assertIn("দ্বিতীয় লাইন।", cleaned)

    def test_removes_title_label_and_its_title_line(self):
        text = "## শিরোনামঃ\nঐতিহ্যের ছায়ায়\n\n## কবিতাঃ\nসাদা চুনের গন্ধ।\n"
        cleaned, *_ , titles = review.clean_segment_text(text, "bengali")
        self.assertNotIn("শিরোনাম", cleaned)
        self.assertNotIn("কবিতাঃ", cleaned)
        self.assertNotIn("ঐতিহ্যের ছায়ায়", cleaned)
        self.assertIn("সাদা চুনের গন্ধ।", cleaned)
        self.assertGreaterEqual(titles, 2)

    def test_removes_poem_label_heading(self):
        text = "## কবিতাঃ\nসাদা চুনের গন্ধ।\n"
        cleaned, _frags, _summary, titles = review.clean_segment_text(text, "bengali")
        self.assertEqual(cleaned, "সাদা চুনের গন্ধ।\n")
        self.assertEqual(titles, 1)

    def test_removes_multiple_leading_title_headings(self):
        text = "## — পর্ব ১ —\n## কবিতাঃ\nমূল কবিতা লাইন।\n"
        cleaned, _frags, _summary, titles = review.clean_segment_text(text, "bengali")
        self.assertEqual(cleaned, "মূল কবিতা লাইন।\n")
        self.assertEqual(titles, 2)

    def test_title_removal_keeps_body_text_verbatim(self):
        body = "প্রথম লাইন।\n\nদ্বিতীয় অনুচ্ছেদ।\n"
        cleaned, _frags, _summary, _titles = review.clean_segment_text(
            "## title\n" + body, "bengali"
        )
        self.assertEqual(cleaned, body)

    def test_title_duplicate_at_tail_is_removed(self):
        # Both headings are title labels, so both are metadata and are removed;
        # the poem body is preserved.
        text = "## শিরোনাম\nকবিতার লাইন।\n\n## শিরোনাম\nকবিতার লাইন।\n"
        cleaned, _frags, _summary, titles = review.clean_segment_text(text, "bengali")
        self.assertNotIn("শিরোনাম", cleaned)
        self.assertEqual(cleaned, "কবিতার লাইন।\n\nকবিতার লাইন।\n")
        self.assertEqual(titles, 2)

    def test_title_removal_does_not_empty_a_poem(self):
        for text in (
            "## প্রাসাদের প্রথম আহ্বান\nপ্রথম লাইন।\n",
            "## কবিতাঃ\nপ্রথম লাইন।\n",
        ):
            cleaned, *_ = review.clean_segment_text(text, "bengali")
            self.assertTrue(cleaned.strip())

    def test_target_language_resolves_from_book_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = Path(tmp) / "workspaces" / "pipeline" / "demo"
            pipeline.mkdir(parents=True)
            (pipeline / "book.json").write_text(
                json.dumps({"language": "Bengali"}), encoding="utf-8"
            )
            original = review.PIPELINE_ROOT
            review.PIPELINE_ROOT = Path(tmp) / "workspaces" / "pipeline"
            try:
                self.assertEqual(review.book_language(pipeline), "Bengali")
                self.assertEqual(
                    review.resolve_target_language("demo"), ("bengali", "bengali")
                )
            finally:
                review.PIPELINE_ROOT = original

    def test_missing_language_raises_instead_of_defaulting(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = Path(tmp) / "workspaces" / "pipeline" / "demo"
            pipeline.mkdir(parents=True)
            (pipeline / "book.json").write_text(
                json.dumps({"form": "poetry"}), encoding="utf-8"
            )
            original = review.PIPELINE_ROOT
            review.PIPELINE_ROOT = Path(tmp) / "workspaces" / "pipeline"
            try:
                with self.assertRaises(ValueError):
                    review.resolve_target_language("demo")
            finally:
                review.PIPELINE_ROOT = original


class TestConfigReport(unittest.TestCase):
    def _make_pipeline(self, root: Path) -> Path:
        pipeline = root / "workspaces" / "pipeline" / "demo"
        chapter = pipeline / "chapters" / "1"
        segment = chapter / "segments" / "1"
        (segment / "latest").mkdir(parents=True)
        (segment / "latest" / "segment.md").write_text("Poem body.\n", encoding="utf-8")
        (segment / "segment.json").write_text(
            json.dumps({"segment_title": "First Segment"}), encoding="utf-8"
        )
        (chapter / "chapter.json").write_text(
            json.dumps({
                "chapter_title": "First Chapter",
                "state": "completed",
                "segments": [{"segment_index": 1, "segment_title": "First Segment"}],
            }), encoding="utf-8",
        )
        (pipeline / "book.json").write_text(
            json.dumps({
                "book_name": "demo",
                "book_long_title": "Demo Book",
                "language": "Bengali",
                "form": "poetry",
                "chapter_count": 1,
                "segment_count": 1,
                "word_target": 500,
                "factory": "online",
                "model": "m",
                "provider": "ollama",
                "chapters": [{"name": "1"}],
            }), encoding="utf-8",
        )
        (pipeline / "progress.json").write_text(
            json.dumps({
                "chapters": [{
                    "chapter_number": 1, "topic": "First Chapter",
                    "status": "written", "file_path": "chapters/1/chapter.md",
                    "written": True, "validated": False, "published": False,
                }],
                "current_chapter": 1,
                "published": False,
            }), encoding="utf-8",
        )
        return pipeline

    def _with_root(self, root: Path):
        original = config_report.PIPELINE_ROOT
        config_report.PIPELINE_ROOT = root / "workspaces" / "pipeline"
        return original

    def _profile_file(self, pipeline: Path) -> Path:
        return pipeline / "profile" / "publish" / "default" / "profile.json"

    def _profile_pages(self, pipeline: Path) -> Path:
        return pipeline / "profile" / "publish" / "default" / "pages"

    def _read_profile(self, pipeline: Path) -> dict:
        return json.loads(self._profile_file(pipeline).read_text(encoding="utf-8"))

    def test_builds_reference_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            original = self._with_root(root)
            try:
                config = config_report.build_config("demo", updated_by="enrich")
            finally:
                config_report.PIPELINE_ROOT = original

            self.assertEqual(config["title"], "Demo Book")
            self.assertEqual(config["book_name"], "demo")
            self.assertEqual(config["updated_by"], "enrich")
            self.assertEqual(config["total_chapters"], 1)
            self.assertEqual(config["current_chapter"], 1)
            chapter = config["chapters"][0]
            self.assertEqual(
                list(chapter.keys()),
                ["chapter_number", "topic", "category", "status", "file_path", "segments"],
            )
            segment = chapter["segments"][0]
            self.assertEqual(
                list(segment.keys()),
                ["segment_number", "segment_title", "file_path", "validated"],
            )
            self.assertEqual(
                segment["file_path"], "chapters/1/segments/1/latest/segment.md"
            )
            self.assertEqual(segment["segment_title"], "First Segment")
            self.assertTrue(segment["validated"])
            # No removed fields sneak back in.
            self.assertNotIn("word_count", segment)
            self.assertNotIn("meta_path", chapter)
            self.assertNotIn("segment_count", chapter)

    def test_sync_writes_once_then_no_ops(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            original = self._with_root(root)
            try:
                self.assertTrue(config_report.sync_config("demo", updated_by="write"))
                self.assertFalse(config_report.sync_config("demo", updated_by="write"))
                path = pipeline / "config.json"
                self.assertTrue(path.is_file())
                path.unlink()
                self.assertTrue(config_report.sync_config("demo", updated_by="write"))
            finally:
                config_report.PIPELINE_ROOT = original

    def test_keeps_context_and_moves_display_onto_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            display = {"version": 1, "name": "demo", "saved_at": "x",
                       "options": {"footer_text": "Keep Me"}}
            (pipeline / "config.json").write_text(
                json.dumps({"context": "curated", "display": display}), encoding="utf-8"
            )
            original = self._with_root(root)
            try:
                config_report.sync_config("demo", updated_by="write")
            finally:
                config_report.PIPELINE_ROOT = original

            config = json.loads((pipeline / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["context"], "curated")
            self.assertNotIn("display", config)
            profile = self._read_profile(pipeline)
            self.assertEqual(profile["book"]["options"]["footer_text"], "Keep Me")

    def test_moves_legacy_printing_section_onto_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            printing = {"version": 1, "name": "demo", "saved_at": "x",
                        "options": {"footer_text": "Renamed"}}
            (pipeline / "config.json").write_text(
                json.dumps({"printing": printing}), encoding="utf-8"
            )
            original = self._with_root(root)
            try:
                config_report.sync_config("demo", updated_by="write")
            finally:
                config_report.PIPELINE_ROOT = original

            config = json.loads((pipeline / "config.json").read_text(encoding="utf-8"))
            self.assertNotIn("printing", config)
            profile = self._read_profile(pipeline)
            self.assertEqual(profile["book"]["options"]["footer_text"], "Renamed")

    def test_moves_legacy_layout_section_onto_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            layout = {"version": 1, "name": "demo", "saved_at": "x",
                      "options": {"footer_text": "Old Name"}}
            (pipeline / "config.json").write_text(
                json.dumps({"layout": layout}), encoding="utf-8"
            )
            original = self._with_root(root)
            try:
                config_report.sync_config("demo", updated_by="write")
            finally:
                config_report.PIPELINE_ROOT = original

            config = json.loads((pipeline / "config.json").read_text(encoding="utf-8"))
            self.assertNotIn("layout", config)
            profile = self._read_profile(pipeline)
            self.assertEqual(profile["book"]["options"]["footer_text"], "Old Name")

    def test_moves_root_profile_and_pages_into_profile_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            (pipeline / "profile.json").write_text(
                json.dumps({"version": 1, "name": "default",
                            "book": {"options": {"footer_text": "From Root"}}}),
                encoding="utf-8",
            )
            blurb = pipeline / "pages" / "blurb" / "blurb.rtf"
            blurb.parent.mkdir(parents=True)
            blurb.write_text("kept\n", encoding="utf-8")
            original = self._with_root(root)
            try:
                config_report.sync_config("demo", updated_by="write")
            finally:
                config_report.PIPELINE_ROOT = original

            self.assertFalse((pipeline / "profile.json").exists())
            self.assertFalse((pipeline / "pages").exists())
            self.assertEqual(
                (self._profile_pages(pipeline) / "blurb" / "blurb.rtf")
                .read_text(encoding="utf-8"),
                "kept\n",
            )
            profile = self._read_profile(pipeline)
            self.assertEqual(profile["book"]["options"]["footer_text"], "From Root")

    def test_derives_bengali_context_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._make_pipeline(root)
            original = self._with_root(root)
            try:
                config = config_report.build_config("demo")
            finally:
                config_report.PIPELINE_ROOT = original
            self.assertEqual(
                config["context"],
                "১টি কবিতা; প্রতিটি কবিতায় ১টি পরিকল্পিত segment; "
                "প্রতি segment-এর word_target 500।",
            )

    def test_falls_back_to_editor_when_no_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            segment = pipeline / "chapters" / "1" / "segments" / "1"
            (segment / "latest" / "segment.md").unlink()
            (segment / "editor").mkdir()
            (segment / "editor" / "segment.md").write_text("Body.\n", encoding="utf-8")
            original = self._with_root(root)
            try:
                config = config_report.build_config("demo")
            finally:
                config_report.PIPELINE_ROOT = original
            self.assertEqual(
                config["chapters"][0]["segments"][0]["file_path"],
                "chapters/1/segments/1/editor/segment.md",
            )

    def test_stages_template_profile_and_pages_after_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            original = self._with_root(root)
            try:
                self.assertFalse((pipeline / "config.json").is_file())
                self.assertTrue(config_report.sync_config("demo", updated_by="write"))
            finally:
                config_report.PIPELINE_ROOT = original

            # The reference profile and its page designs are staged inside the
            # book's own profile folder, not beside the pipeline state.
            pages = self._profile_pages(pipeline)
            self.assertTrue((pages / "publisher" / "title.rtf").is_file())
            self.assertTrue((pages / "cover" / "front.jpg").is_file())

            config = json.loads((pipeline / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["updated_by"], "write")
            self.assertEqual(config["book_name"], "demo")
            self.assertEqual(config["title"], "Demo Book")
            # Print setup never shares the configuration file.
            for key in ("display", "printing", "layout", "pages", "overriden"):
                self.assertNotIn(key, config)

            profile = self._read_profile(pipeline)
            # A print profile describes the publisher side of the book only: the
            # identity of the author's content belongs to the pipeline state.
            self.assertEqual(profile["version"], config_report.PROFILE_VERSION)
            self.assertNotIn("content", profile)
            self.assertEqual(profile["book"]["display_name"], "Demo Book")
            # The logo kept beside the profile travels with it.
            self.assertTrue((self._profile_file(pipeline).parent / "logo.jpg").is_file())
            # A template's foreign cover path is replaced by the staged cover.
            self.assertEqual(
                profile["book"]["options"]["front_cover_image_path"],
                "pages/cover/front.jpg",
            )
            # Every page entry is recorded relative to the profile folder.
            for page in profile["book"]["pages"]:
                self.assertTrue(page["file_path"].endswith("/"))
                self.assertFalse(page["file_path"].startswith("D:"))
                for path in page["paths"]:
                    self.assertFalse(path["file_path"].startswith("D:"))
            publisher = next(
                page for page in profile["book"]["pages"]
                if page["file_path"] == "pages/publisher/"
            )
            self.assertEqual(
                [path["file_path"] for path in publisher["paths"]],
                ["pages/publisher/copyright.rtf", "pages/publisher/dedicate.rtf",
                 "pages/publisher/publisher.rtf", "pages/publisher/title.rtf"],
            )
            # Every page records what it is printed as; the `format` of its
            # folder is only the preference it falls back on.
            for page in profile["book"]["pages"]:
                for path in page["paths"]:
                    self.assertTrue(path["content_type"])
            self.assertEqual(
                [path["content_type"] for path in publisher["paths"]],
                ["application/rtf"] * 4,
            )
            cover = next(
                page for page in profile["book"]["pages"]
                if page["file_path"] == "pages/cover/"
            )
            self.assertEqual(
                [path["content_type"] for path in cover["paths"]],
                ["image/jpeg"],
            )
            # The cover is the front image alone; the back cover is kept and
            # printed from the back cover folder, under a tab of its own.
            self.assertEqual(
                [path["file_path"] for path in cover["paths"]],
                ["pages/cover/front.jpg"],
            )
            back_cover = next(
                page for page in profile["book"]["pages"]
                if page["file_path"] == "pages/backcover/"
            )
            self.assertEqual(
                [path["file_path"] for path in back_cover["paths"]],
                ["pages/backcover/back.jpg"],
            )
            self.assertEqual(
                profile["book"]["options"]["back_cover_image_path"],
                "pages/backcover/back.jpg",
            )

    def test_staging_never_overwrites_a_pipeline_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            title = self._profile_pages(pipeline) / "publisher" / "title.rtf"
            title.parent.mkdir(parents=True)
            title.write_text("kept\n", encoding="utf-8")
            self._profile_file(pipeline).write_text(
                json.dumps({"version": 1, "name": "default",
                            "book": {"options": {"footer_text": "Mine"}}}),
                encoding="utf-8",
            )
            original = self._with_root(root)
            try:
                config_report.sync_config("demo", updated_by="write")
            finally:
                config_report.PIPELINE_ROOT = original
            self.assertEqual(title.read_text(encoding="utf-8"), "kept\n")
            profile = self._read_profile(pipeline)
            self.assertEqual(profile["book"]["options"]["footer_text"], "Mine")

    def test_older_profile_loses_the_content_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            self._profile_file(pipeline).parent.mkdir(parents=True)
            self._profile_file(pipeline).write_text(
                json.dumps({
                    "version": 1,
                    "name": "default",
                    "content": {"name": "demo", "reference": "demo",
                                "language": "Bengali", "form": "poetry",
                                "source": "pipeline", "parser": "markdown"},
                    "book": {"author": "A. Writer", "options": {"footer_text": "Mine"}},
                }),
                encoding="utf-8",
            )
            original = self._with_root(root)
            try:
                config_report.sync_profile("demo")
            finally:
                config_report.PIPELINE_ROOT = original
            profile = self._read_profile(pipeline)
            # A print profile holds the publisher side of the book, never the
            # identity of the author's writing.
            self.assertNotIn("content", profile)
            self.assertEqual(profile["version"], config_report.PROFILE_VERSION)
            self.assertEqual(profile["book"]["author"], "A. Writer")
            self.assertEqual(profile["book"]["options"]["footer_text"], "Mine")
            # A profile written before version 3 gains the source block, so the
            # copy that travels into a published edition can be followed back.
            self.assertEqual(
                profile["source"],
                {"book_name": "demo", "source_format": "pipeline",
                 "source_path": "demo", "version": None},
            )

    def test_profile_records_the_pipeline_it_prints_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            original = self._with_root(root)
            try:
                config_report.sync_profile("demo")
            finally:
                config_report.PIPELINE_ROOT = original
            profile = self._read_profile(pipeline)
            # `source_path` is relative to workspaces/pipeline, so the workspace
            # can be moved to another machine without the profile changing.
            self.assertEqual(
                profile["source"],
                {"book_name": "demo", "source_format": "pipeline",
                 "source_path": "demo", "version": None},
            )
            # Re-deriving the profile keeps the same source.
            self.assertFalse(config_report.sync_profile("demo"))

    def test_content_type_is_typed_from_the_file_not_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            publisher = self._profile_pages(pipeline) / "publisher"
            publisher.mkdir(parents=True)
            (publisher / "colophon.rtf").write_text("{\\rtf1}", encoding="utf-8")
            (publisher / "seal.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            original = self._with_root(root)
            try:
                config_report.sync_profile("demo")
            finally:
                config_report.PIPELINE_ROOT = original
            profile = self._read_profile(pipeline)
            types = {
                path["file_path"]: path["content_type"]
                for page in profile["book"]["pages"]
                for path in page["paths"]
            }
            self.assertEqual(types["pages/publisher/colophon.rtf"], "application/rtf")
            # An image put in a folder of designs still prints as an image.
            self.assertEqual(types["pages/publisher/seal.png"], "image/png")

    def test_recorded_content_type_is_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline = self._make_pipeline(root)
            publisher = self._profile_pages(pipeline) / "publisher"
            publisher.mkdir(parents=True)
            (publisher / "title.rtf").write_text("{\\rtf1}", encoding="utf-8")
            self._profile_file(pipeline).parent.mkdir(parents=True, exist_ok=True)
            self._profile_file(pipeline).write_text(
                json.dumps({
                    "version": config_report.PROFILE_VERSION,
                    "name": "default",
                    "book": {"pages": [{
                        "order": 1, "file_path": "pages/publisher/", "format": "rtf",
                        "paths": [{"order": 1, "file_path": "pages/publisher/title.rtf",
                                   "content_type": "text/rtf"}],
                    }]},
                }),
                encoding="utf-8",
            )
            original = self._with_root(root)
            try:
                config_report.sync_profile("demo")
            finally:
                config_report.PIPELINE_ROOT = original
            profile = self._read_profile(pipeline)
            publisher = next(
                page for page in profile["book"]["pages"]
                if page["file_path"] == "pages/publisher/"
            )
            # A page keeps the type it records, even when its extension says
            # something else; only a page without one is typed.
            self.assertEqual(publisher["paths"][0]["content_type"], "text/rtf")

    def test_content_type_falls_back_on_the_format_of_its_folder(self):
        self.assertEqual(config_report.content_type_of("pages/publisher/title.rtf"), "application/rtf")
        self.assertEqual(config_report.content_type_of("pages/cover/front.jpg"), "image/jpeg")
        self.assertEqual(config_report.content_type_of("pages/index/page.xyz", "markdown"), "text/markdown")
        self.assertEqual(config_report.content_type_of("pages/blurb/page.xyz", "rtf"), "application/rtf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
