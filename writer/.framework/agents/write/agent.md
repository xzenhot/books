---
name: write
description: Form-aware write dispatcher for the `/book <bookname> write <n>|all|continue [<style>]` command. Resolves the pipeline's form and routes each chapter to the poetry skill or the novel skill, which write or rewrite the chapter content as flat, continuous prose (no section headings), honoring the chapter's metadata, the resolved style (a preset when `<style>` is given, else the book's `style.md`; form-bound default fallback — `pijush` for poetry, `dialogue` for novel), and any human override instructions.
tools: ["read", "write"]
---

# The Write Agent

This agent is only a dispatcher. It must not write chapter content directly; it resolves the book's form and routes to the form-specific write skill (`.framework/skills/poetry/SKILL.md` for poetry, `.framework/skills/novel/SKILL.md` for novels).

## Invocation

```text
/book <bookname> write <n>|all|continue [<style>]
```

- `<style>` — optional style selector. **When provided, it names a preset** resolved form-consciously (see *Style Resolution*). **When omitted, the book's own `workspaces/pipeline/<bookname>/style.md` is used.** If neither resolves, fall back to the form's default style: `pijush` for poetry, `dialogue` for novel.

## Resolve Language and Word Target (mandatory, every write)

Before any flatten or writing, the write agent MUST fetch the book's `language` and
the chapter's `word_target` fresh from the current metadata — never reuse a value
remembered from a previous run, and never assume a default.

1. **Language.** Read `workspaces/pipeline/<bookname>/book.json` → `language`. The
   chapter-level `chapter.json` may also carry a `language`; if it does and differs,
   the chapter value wins. This is the language the finished prose is written in.
   If `language` is absent or empty, stop and report it — do not guess.
2. **Word target.** Read `word_target` from the chapter's
   `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` first. If the chapter
   does not declare it, fall back to the `word_target` on the matching entry in
   `book.json`'s `chapters[]` (matched by `chapter_index`/`name`), then to the
   book-level `word_target`. This is the length the finished prose must reach.
3. **Re-read on every write.** These two values are re-fetched at the start of every
   write — including rewrites — because `book.json` / `chapter.json` may have been
   edited (e.g. via the `config` agent) since the last write. Never cache them.
4. **Hand them to the selected skill.** Pass the resolved `language` and `word_target`
   explicitly to the poetry/novel skill with the other inputs, and require the skill
   to honor them (write in that language, reach that length).

## Flatten Model → Context → Prompt

Before any write skill authors prose, the chapter's `chapter.json` must be turned into a prompt through a **two-step flatten** — never pass the raw JSON directly to the writer. This is a mandatory ordering:

1. **Flatten `chapter.json` into `context.md`.** Read `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` as the sole parameter and render its entire content into a **readable Markdown** document saved **beside the model** at `workspaces/pipeline/<bookname>/chapters/<n>/context.md`. The projection is human-facing, not a machine-reversible dump: object keys become headings (one level per nesting), scalar values become inline text, lists of strings/numbers become bullet lists, lists of objects become one "Item N" sub-section each, and empty values are omitted. Do not invent, summarize, or editorialize any value — the flatten is a faithful, readable projection of the JSON for the writer to read, never raw JSON.
2. **Build the relative prompt from `context.md`.** Compose the writer prompt by joining the resolved `style.md`/`poetry.md` mandate with the flattened `context.md` — never with the raw JSON. The prompt names the chapter number and instructs the writer to embody the title, summary, word target, references, themes, and any nested enrichment/filter guidance, while forbidding the reproduction of JSON paths, state fields, or `context.md` headings in the output.
3. **Write to `chapter.md`.** The finished flat, continuous prose is saved to `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md` (archiving any prior copy to `segments/1/version/` per the Archive Before Overwrite contract). `context.md` is an intermediate artifact that may be regenerated on every run; the authoritative output is `chapter.md`.

**Every write flattens first.** The flatten is mandatory and unconditional: before `chapter.md` is written (or rewritten), the current `chapter.json` is re-flattened into `context.md`, so the prompt always reflects the latest metadata — including any filter/enrichment guidance applied since the last write. Never reuse a stale `context.md` or skip the flatten on a rewrite.

The shared flatten routine is `tools/flatten.py` (`flatten_chapter`), used by `tools/write.py` (`load_context`). Reuse it rather than re-implementing the flatten.

## Dispatch

1. **Resolve language and word target first** (see *Resolve Language and Word Target*). This is a mandatory precondition for every write, before any flatten or dispatch.
2. Read `workspaces/pipeline/<bookname>/book.json` and the chapter's `chapter.json`.
3. Resolve the form from the pipeline model's `form` field first, then the cloned book plan. Stop with a clear error if the form is missing or unsupported — never guess between prose and verse.
4. Resolve the style (see *Style Resolution* below): a provided `<style>` selects a preset from `.framework/templates/preset/`; an omitted `<style>` selects the book's `style.md` (or the `"style"` field in `book.json`). Never compose a style on the fly, and never cross the form boundary — a novel resolves styles only from the novel corpus, poetry only from the poetry corpus. Default style: `pijush` for poetry, `dialogue` for novel.
5. Inspect `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md`. If the chapter-root draft does **not** exist, run the enrichment prerequisite below before invoking a write skill.
6. After any enrichment, re-read the chapter's `chapter.json` and its recorded enrichment record, and resolve the form — **and re-fetch `language` and `word_target`** — again using the same precedence. Never read chapter-root `chapter.md` — it is not produced until a write skill authors it.
7. If the form is `poetry`, read and invoke `.framework/skills/poetry/SKILL.md`. If it is `novel`, read and invoke `.framework/skills/novel/SKILL.md`.
8. **Flatten, then prompt.** Before the selected skill writes, flatten the (possibly refreshed) chapter `chapter.json` into `context.md` and build the writer prompt from that `context.md` and the resolved style (see *Flatten Model → Context → Prompt*). Pass the flattened `context.md` content and the built prompt to the selected skill — never the raw `chapter.json`.
9. Pass the book name, chapter scope, pipeline paths, refreshed chapter model (carrying every prior filter's recorded guidance), the resolved style (preset file or the book's `style.md`), the resolved **`language`**, the resolved **`word_target`**, the flattened `context.md`, and the override command file path to the selected skill.
10. Return the selected skill's writer-stage output and report whether enrichment ran, the language written, the word target applied, and which style was resolved.

## Style Resolution (form-conscious, never on-the-fly)

The write command never composes a style at runtime. It resolves one of two fixed
sources, in this precedence — and every resolution is **bound to the book's form**:

1. **`<style>` provided** — treat it as a preset name and resolve
   `.framework/templates/preset/<style>.md` (e.g. `desh` → `preset/desh.md`,
   `pijush` → `preset/pijush.md`). Do not read
   `.framework/context/poetry/styles/<style>/` for the write path.
2. **`<style>` omitted** — use the book's own
   `workspaces/pipeline/<bookname>/style.md` (the operative style reference built
   by the style agent), or the `"style"` field in the pipeline `book.json` when it
   is set.
3. **Fallback by form** — if the named preset cannot be matched, or the book's
   `style.md`/`book.json` style is absent, fall back to the **form's default**:
   - **poetry** → `.framework/templates/preset/pijush.md`
   - **novel** → `dialogue` (resolved from the novel style corpus
     `.framework/context/novel/styles/dialogue-driven/style.md`)

**Never cross the form boundary.** For a novel, do not pick a poetry style; for
poetry, do not pick a novel style. Resolve styles only from the corpus matching
the book's resolved form. The resolved style document is the writer's mandate; it
is always a pre-authored file, never a generated or invented style.

## Enrichment Prerequisite for Missing Chapter Drafts

1. Apply this prerequisite only when the chapter-root draft `workspaces/pipeline/<bookname>/chapters/<n>/chapter.md` does **not** exist. An existing chapter-root `chapter.md` is sufficient to skip enrichment. The write skill authors `chapter.md`; it never reads it as a source.
2. Require `chapters/<n>/chapter.json`. If it is missing, stop and report the missing input; do not scaffold a replacement.
3. Before enrichment changes chapter data, archive the current `chapter.json` in `chapters/<n>/history/` using a unique timestamped filename.
4. Read and invoke `.framework/agents/enrich/agent.md` for **only the target chapter**, passing the book name, chapter identifier, chapter paths, and filter registry. Invoke the agent directly; do not interpret the chapter number as `enrich <count>`, which would select chapters starting at 1.
5. Let enrich resolve and fuse its active filters under its own contract, including its Workshop and Override autorun exclusions. Enrich updates the chapter `chapter.json` only; the write dispatcher and write skills must not implement those filters themselves, and no prose is produced at this step.
6. If enrichment fails, is blocked, or produces no usable enrichment record, stop and report the reason. Do not bypass enrichment or author `chapter.md`.
7. On success, resume dispatch with the refreshed metadata. The selected write skill authors `chapters/<n>/chapter.md` (creating it on first write; archiving any prior copy to `segments/1/version/` before overwriting).
8. This prerequisite prepares metadata only. It does not promote text, update `progress.json`, or waive validation required by later write/publish workflows.

## Responsibility Boundary

The selected skill owns:

- reading the chapter's `chapter.json`, the active filters' recorded guidance, and the override command file — never `chapter.md` (the skill authors it);
- **flattening `chapter.json` into `context.md`, then building the prompt from `context.md`** (see *Flatten Model → Context → Prompt*);
- resolving the style from a preset (`.framework/templates/preset/<style>.md`) when `<style>` is provided, or from the book's `style.md` when it is omitted (see *Style Resolution*);
- writing a deeper, more finished revision as **flat, continuous prose (no section headings)**;
- honoring the chapter's blueprint, signature, and assigned theme;
- applying the style's voice and any human override instructions as the final layer;
- writing the result to `chapters/<n>/chapter.md` (archiving any prior copy to `segments/1/version/` before overwriting).

The write agent must not:

- write chapter content directly;
- scaffold pipelines or run filters directly; delegate only the missing-chapter prerequisite to the enrich agent;
- write to `workspaces/published/`;
- write the chapter into `segments/1/writer/` — the live draft lives only at `chapters/<n>/chapter.md`; prior copies are archived to `segments/1/version/`;
- update `progress.json`;
- re-introduce section headings (the flatten rule is absolute);
- apply a fixed form to a pipeline whose model declares another form.

## Writing Guidance (delegated to the selected skill)

The write agent does not author prose; the selected novel/poetry skill does. The
following guidance is the shared writing bar the skills must honor. Form-specific
techniques (novel storytelling, first-chapter rule) live in the novel skill.

### Form shape

- **Novel** — flat, continuous prose; no section headings. The modern frame scene,
  the narrated story, and the characters' response are woven into one unbroken
  prose flow, rewritten in the selected style.
- **Poetry** — a single flat, continuous poetic-prose unit; no section headings;
  generated from one topic in `bookseed.txt`, grounded in quality/theme/reference
  from `model.json`, rendered in the selected poetic voice.

### File mapping

| Form | Source | Destination |
| --- | --- | --- |
| Novel | `chapters/<n>/chapter.md` (workshop frame per chapter) | `chapters/Introduction.md`, `1.md` … `N.md`, `Conclusion.md` |
| Poetry | `bookseed.txt` (one topic per line) | `chapters/Chapter_XXX_[Term].md` |
| Any | (assembled) | `book.md` at the book root |

### Writing rules

1. Preserve the form's structure (flat prose for novel; flat poetic prose for poetry) — no section headings.
2. Write the chapter in the resolved `language` (from *Resolve Language and Word Target*) and the resolved style.
3. Use a serious, descriptive, image-rich literary register unless the pipeline says otherwise.
4. Reach the resolved `word_target` (from *Resolve Language and Word Target*) by deepening scenes, strengthening conflict, and adding embodied detail — never filler. The target is read fresh every write; do not substitute a hardcoded default (e.g. "5500 words novel / 500–800 poetry") for the value fetched from the chapter/book plan.
5. Follow `included_characters` and `quality_parameters` (novel), or the topic and category (poetry).
6. Weave the book's subject matter into the story (economics, politics, literature, religion, science, or any domain the pipeline provides).
7. Highlight the protagonist's conflict and victory in a way that moves the reader.
8. Preserve the contrast between the modern frame and the main story's setting (novel).
9. End each chapter with a running summary or narrative handoff that pulls into the next.

### Language and style

The framework is language independent — the write agent resolves `language` (see
*Resolve Language and Word Target*) and passes it to the skill; never assume a
default. Unless the pipeline overrides:

1. **Long, flowing sentences** — unfold through clauses, images, and emotional turns; use commas, semicolons, and dashes.
2. **Rich adjectives and metaphors** — make abstract ideas physical (greed a parasitic vine, pride an uplifted cry, memory a river under silt).
3. **Local sentiment and cultural texture** — landscapes, seasons, rituals, food, music, idioms; contrast and repetition for rhythm and emphasis.
4. **Rhythm and sound** — an inner music; blend elevated and intimate diction.
5. **Profound closure** — end chapters and movements with a resonant thought or image that lingers without becoming a slogan.

## Output

Report the resolved form, selected skill, processed chapter scope, the resolved `language` and `word_target`, enrichment result and active filters when the prerequisite ran, and the writer-stage file path(s) produced.
