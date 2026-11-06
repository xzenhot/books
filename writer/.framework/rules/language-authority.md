# Language Authority

The book's **output language is declared in exactly one place**: the `language`
field of the book plan (`book.json`). Every agent, skill, filter, and template
must resolve it from there and nowhere else.

This rule is binding on all commands, in both forms, in every phase.

## The Single Source

| Phase | Read `language` from |
|---|---|
| Pipeline (write, style, translate, enrich, filter, publish, preview) | `workspaces/pipeline/<bookname>/book.json` |
| Backlog (init, layout) | `workspaces/backlog/<bookname>/book.json` |

A chapter-level override, when one exists, may narrow the language for that one
unit:

1. `chapters/<n>/chapter.json` → `language` — wins for that chapter only.
2. `book.json` → `language` — the book-wide authority.

If neither declares a language, **stop and report** it. Never default silently to
English, Bengali, or any other language.

## What Never Determines Language

These files carry craft, voice, and structure. They **must not** state, imply, or
override the output language:

| File | Owns | Never owns |
|---|---|---|
| `override.md` (backlog and pipeline) | Craft mandate — voice, opening, line breaks, repetition, line count, symbol, register | Output language, form, word target |
| `style.md` / `styles/<style>/style.md` | Structure — syntax, meter, line/stanza shape, rhyme scheme, register | Output language, subject matter |
| `signature.md` | Voice — movement, motifs, diction, pattern | Output language, meter, rhyme |
| `bookseed.md` | Vocabulary and phrase seed — always rendered in the book's `language` | Output language, subject matter |

The language these files are *written in* has no bearing on the language of the
generated poem or chapter. An `override.md` written in Bengali can govern an
English book, and vice versa.

## Prohibited Wording

Do **not** introduce a sentence like *"Write in English"*, *"Write in Bengali"*,
*"the language of the book is X"*, or *"translate to X"* into `override.md`,
`style.md`, `signature.md`, or any template that feeds them. When a file needs to
name the language rule at all, it defers:

```text
Write in the language declared by book.json → language. This file never sets the
output language.
```

A language instruction found in one of these files is a **defect**, not a
directive. The resolving agent ignores it, reports it, and — when it has write
access — repairs that line to the deferring form above.

## Seeding And Derivation1. **init seeds `override.md`.** Reseed it from `gist.md`/`storyline.md` for
   premise, subject, figures, and form. Do **not** encode `language` into it —
   even though `book.json` declares one. The plan is the language record; the
   override is the craft record.
2. **layout Phase 2 derives the pipeline `override.md`.** Same rule: derive form,
   register, signature, and subject matter from the pipeline `book.json`, and
   leave language out.
3. **Scaffold clones `override.md`.** The clone is byte-faithful; if the source
   carries a language directive, the defect propagates. Report it at clone time.
4. **Enrich re-grounds `override.md`** only for subject matter (Step 4 of the
   enrich contract). It never adds or edits a language directive.
5. **Enrich derives `bookseed.md` in the book's language.** The derived
   `<!-- bookseed:derived -->` block is rendered in `book.json` → `language`
   and its own script. The language of the enrichment values that feed it is
   irrelevant — an English enrichment pass over a Bengali book yields a Bengali
   seed. The four category headings stay in their fixed English form so the block
   remains locatable. See *Derived Artifacts Follow The Book's Language* below.

## Derived Artifacts Follow The Book's Language

Any artifact **generated from** enrichment, filtering, or analysis — the
`bookseed.md` lexicon above all — is rendered in the book's declared language, not
in the language of the analysis that produced it. Internal keys (`book.json`,
`chapter.json`) stay in English so the schema stays stable; prose values that the
writer will actually read follow `language`.

| Artifact | Keys/schema | Human-readable values |
|---|---|---|
| `book.json`, `chapter.json` | English | follow `language` when prose |
| `bookseed.md` derived block | fixed English headings | follow `language` |
| `override.md` | — | craft wording; never sets language |
| `chapters/<n>/chapter.md` | — | follow `language`, always |

## One File Per Artifact

`override.md` is Markdown and is the only extension. There is no `override.txt`
sibling — a `.txt` twin is a defect from an older contradictory instruction
("the output is a `.txt` file"). When both exist, `override.md` is authoritative;
the `.txt` is redundant and should be reported for removal, never read as input.

## Audit

Every write path re-reads `language` on **every** invocation, before composing.
Never cache it across commands, and never carry a previous chapter's language
forward to the next.
