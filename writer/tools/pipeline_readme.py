"""Render the pipeline map (`README.md`) for a scaffolded book pipeline.

Scaffold writes ``workspaces/pipeline/<bookname>/README.md`` so the pipeline is
self-describing: what each root file, chapter folder, and runtime registry holds,
and which agent owns it. The document is book-specific (form, chapter count,
filter/quality chains, style), not a static template.

Ownership rule: a README that still carries the generator marker is refreshed on
the next scaffold run, because its facts (counts, chains) are scaffold output. A
README without the marker is treated as hand-written and is never overwritten.
"""

# Load the workspace .env and force UTF-8 output (see tools/env.py).
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from env import bootstrap as _env_bootstrap  # noqa: E402
_env_bootstrap()
from pathlib import Path

from quality import atomic_bytes, audit_timestamp, read_json

MARKER = "<!-- generated-by: scaffold; remove this line to keep a hand-written README -->"

FORM_LABEL = {"poetry": "poetry", "novel": "novel"}


def _list(items):
    return " → ".join(f"`{item}`" for item in items) if items else "_none declared_"


def _chapter_root_rows(form):
    rows = [
        ("`chapter.json`", "Runtime state for this chapter: identity, `chapter_title`, "
                           "`chapter_summary`, `word_target`, `state`, and the live `segments` list."),
        ("`chapter.md`", "The live working draft. Created and revised by the write/chapter/poet path "
                         "(workshop may seed it when absent). Filters never read it."),
        ("`history/`", "Superseded `chapter.md` and model snapshots, written before anything overwrites "
                       "the live draft. Immutable; never audit-stamped."),
    ]
    if form != "poetry":
        rows.insert(1, ("`mood.json`",
                        "Segment planning: how the chapter is broken into segments, kept for continuity."))
    rows.append(("`model.json`", "Legacy chapter-model name. Still read when `chapter.json` is absent; "
                                 "scaffold does not create it for new pipelines."))
    return rows


def _segment_rows():
    return [
        ("`segment.json`", "Runtime state for this segment (level, state, chapter/segment index)."),
        ("`writer/`", "Writer-stage output: the finished copy of the draft for this segment."),
        ("`editor/`", "Editor and review commentary, including content quality scores."),
        ("`translator/`", "Translated derivatives of the latest draft, named by language "
                          "(`en.md`, `bn.md`, …)."),
        ("`version/`", "Promoted snapshots of the segment's published output (`chapter_v<k>.md`)."),
    ]


def render(bookname, *, form="poetry", chapter_count=None, word_target=None,
           filter_chain=None, quality_chain=None, style=None, factory=None,
           updated_by="scaffold", updated_date=None):
    """Return the pipeline `README.md` body for *bookname*.

    Only facts declared in the book plan are stated; nothing about the book's
    content is invented here.
    """
    form = form if form in FORM_LABEL else "poetry"
    filter_chain = list(filter_chain or [])
    quality_chain = list(quality_chain or [])
    updated_date = updated_date or audit_timestamp()
    unit = "poem" if form == "poetry" else "chapter"

    lines = [
        f"# Pipeline — {bookname}",
        "",
        f"- **updated_by:** {updated_by}",
        f"- **updated_date:** {updated_date}",
        "",
        f"This folder is the live **{form} pipeline** for `{bookname}`. It is a self-contained "
        "snapshot: after scaffold, every later command (`enrich`, `filter`, `write`, `style`, "
        "`translate`, `publish`) reads and writes here and never falls back to "
        f"`workspaces/backlog/{bookname}/`. If a file listed below is missing, the fix is a "
        "re-scaffold — not reading the backlog.",
        "",
        "## Book facts",
        "",
        "| Key | Value |",
        "|---|---|",
        f"| Book | `{bookname}` |",
        f"| Form | `{form}` |",
        f"| {unit.capitalize()}s scaffolded | {chapter_count if chapter_count is not None else '_see book.json_'} |",
        f"| Word target per {unit} | {word_target if word_target is not None else '_declared per chapter in book.json_'} |",
        f"| Style | `{style}` |" if style else "| Style | _not declared_ |",
        f"| Execution mode (`factory`) | `{factory}` |" if factory else "| Execution mode (`factory`) | _unset — treated as `online`_ |",
        "",
        "## Root files",
        "",
        "| File | Significance |",
        "|---|---|",
        "| `book.json` | The authoritative plan for this pipeline: identity, `form`, `factory`, "
        "`chapter_count`, the `chapters[]` plan, `word_target`, `filter_chain`, and "
        "`quality_chain`. Cloned from the backlog and stamped `scaffold`. |",
        "| `progress.json` | Progress ledger: one entry per chapter with `status`, topic, and draft "
        "path. Updated by `write` and `publish`. |",
        "| `gist.md` | The seed premise: one-sentence gist, short expansion, author comment. |",
        "| `storyline.md` | The full narrative foundation (novel) or thematic grounding (poetry) — "
        "the source for chapter intent. |",
        "| `override.md` | The author's master prompt: mandated voice, diction rules, and craft "
        "directives. Exempt from audit stamping. |",
        "| `bookseed.md` | The book's vocabulary and phrase seed. `enrich` appends a derived lexicon "
        "block. Plain text; exempt from audit stamping. |",
        "| `signature.md` | The selected style's authorial signature, copied from "
        "`.framework/editor/<form>/styles/<style>/` and stamped `scaffold`. |",
        "| `README.md` | This map. Refreshed by scaffold while the generator marker is present. |",
        "",
        "## Folders",
        "",
        "| Folder | Significance |",
        "|---|---|",
        "| `chapters/` | One folder per "
        f"{unit}, named by chapter index (`1` … `{chapter_count if chapter_count else 'N'}`). "
        "Holds the live draft and its runtime state. |",
        "| `filters/` | Filter registry plus per-filter output folders. Scaffold creates only "
        "`filters/filters.json`; each filter creates `filters/<name>/` on its first run. |",
        "| `qualities/` | Quality-dimension registry plus per-dimension folders. Scaffold creates "
        "only `qualities/qualities.json`; each dimension creates `qualities/<name>/` on first use. |",
        "| `layout/` | The form-tool templates cloned from `.framework/templates/backlog/v1/layout/` "
        "— prompts, lenses, twists, and schemas that `enrich` and `write` consume. Keeps the "
        "pipeline self-contained. |",
        "",
        f"## Chapter layout (`chapters/<n>/`)",
        "",
        "| Path | Significance |",
        "|---|---|",
    ]
    lines += [f"| {path} | {meaning} |" for path, meaning in _chapter_root_rows(form)]
    lines += [
        "",
        "### Segment layout (`chapters/<n>/segments/1/`)",
        "",
        "Every chapter owns at least one segment folder. Poetry always has exactly one (`1`).",
        "",
        "| Path | Significance |",
        "|---|---|",
    ]
    lines += [f"| {path} | {meaning} |" for path, meaning in _segment_rows()]
    lines += [
        "",
        "## Runtime registries",
        "",
        "`filters/filters.json` declares the ordered filter chain; `qualities/qualities.json` "
        "declares the quality dimensions for this form. Each entry carries `order`, `name`, and "
        "`autorun` (filters also carry the `agent` skill path). Setting `autorun: false` skips an "
        "entry in `filter *` / `filter all`; naming it explicitly still runs it.",
        "",
        f"- **Filter chain:** {_list(filter_chain)}",
        f"- **Quality chain:** {_list(quality_chain)}",
        "",
        "## Read/write ownership",
        "",
        "| Actor | May write | Must not touch |",
        "|---|---|---|",
        "| `scaffold` | Pipeline structure, root planning files, the two registries, this README | "
        "Filter output, finished drafts, `workspaces/published/` |",
        "| `filter:<name>` | Its own `filters/<name>/` folder and chapter **models** | `chapter.md`, "
        "another filter's folder, `workspaces/published/` |",
        "| `enrich` | Chapter models and the derived lexicon block in `bookseed.md` | `chapter.md` |",
        "| `write` / `chapter` / `poet` | `chapter.md`, `segments/1/writer/`, `history/`, "
        "`progress.json` | `workspaces/backlog/` |",
        "| `review` / `humanize` | Editor commentary and language corrections | "
        "`workspaces/published/` |",
        "| `publish` | `workspaces/published/<bookname>/<version>/` and `progress.json` | Pipeline "
        "drafts |",
        "",
        "## Command surface for this pipeline",
        "",
        "```text",
        f"/book {bookname} enrich *            # fuse active filters into one guidance pass",
        f"/book {bookname} filter <name> all|*|<n>",
        f"/book {bookname} write <n>|all|continue [<style>]",
        f"/book {bookname} review *|all|<n>",
        f"/book {bookname} humanize *|all|<n>",
        f"/book {bookname} translate <n>|all|continue <language>",
        f"/book {bookname} publish [<language>]",
        "```",
        "",
        "Outputs never become reader-facing here: finished text is promoted only into "
        f"`workspaces/published/{bookname}/<version>/` by `publish`, after the quality gate passes.",
        "",
        MARKER,
        "",
    ]
    return "\n".join(lines)


def write_for_pipeline(pipeline, bookname, plan, filter_chain=None, quality_chain=None,
                       stamp=None, logger=print):
    """Write `README.md` into *pipeline* from *plan*.

    Returns ``True`` when the file was written. An existing README without the
    generator marker is left untouched (hand-written content wins).
    """
    pipeline = Path(pipeline)
    target = pipeline / "README.md"
    if target.exists():
        try:
            existing = target.read_text(encoding="utf-8-sig")
        except OSError:
            return False
        if MARKER not in existing:
            logger("Preserving hand-written pipeline README")
            return False

    chain = filter_chain if filter_chain is not None else plan.get("filter_chain")
    qualities = quality_chain if quality_chain is not None else plan.get("quality_chain")
    text = render(
        bookname,
        form=plan.get("form", "poetry"),
        chapter_count=plan.get("chapter_count"),
        word_target=plan.get("word_target"),
        filter_chain=chain,
        quality_chain=qualities,
        style=plan.get("style"),
        factory=plan.get("factory"),
        updated_date=stamp,
    )
    atomic_bytes(target, text.encode("utf-8"))
    return True


__all__ = ["MARKER", "render", "write_for_pipeline"]
