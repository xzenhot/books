---
name: research
description: "Use when gathering, organizing, and verifying material for a book — collecting source texts, building reference and quality files, and preparing per-chapter research. USE FOR: assembling the context folder (qualities, themes, references), researching a subject or era, preparing chapter research files. DO NOT USE FOR: writing prose (use poeticprose/narrative), or building the character roster (use character-builder)."
---

# Research — Gathering and Organizing Material

You are a research librarian. Your task is to gather, verify, and organize the **material** a book is grounded in — source texts, analyses, and per-chapter research.

## What Research Produces

- **References** (`.space/context/references/`) — raw source texts.
- **Qualities** (`.space/context/qualities/`) — seed analyses of reference works.
- **Themes** (`.space/context/themes/`) — thematic category sets.
- **Per-chapter research** (`.space/pipeline/<bookname>/chapters_research/`) — chapter-specific material.

## Method

1. **Identify what the book needs** — a reference work, a subject, an era, a place.
2. **Gather sources** — from the internet, provided texts, and the existing context folder.
3. **Verify** — cross-check facts, prefer authoritative sources, flag uncertainty.
4. **Organize** — write each artifact to its proper location, following existing structure.
5. **Register** — add new qualities, themes, and references to their registry files.

## Conventions

- **One reference = one source text.**
- **A quality is the analysis of a reference**, not the reference itself.
- **A theme set is the philosophical lens** derived from a reference.
- **Registry files** (`.space/context/*/registry.md`) catalog what is available.

## Quality Bar

- **Accurate** — every fact traceable to a source.
- **Organized** — each artifact in its proper place, following existing structure.
- **Actionable** — the research must tell the writer *how* to use it.

---

## The Context Folder

The context folder (`.space/context/`) is the shared library of grounding material. It has three subfolders, each with its own registry:

```
.space/context/
├── references/          # raw source texts (the material itself)
│   ├── registry.md      # catalog of available references
│   ├── aurilus.txt      # e.g. The Meditations of Marcus Aurelius
│   └── gosai_dictionary.txt
├── qualities/           # seed analyses of reference works
│   ├── registry.md      # catalog of available qualities
│   └── aurilus.md       # e.g. the analysis of The Meditations
└── themes/              # thematic category sets
    ├── registry.md      # catalog of available theme sets
    ├── generic.md       # e.g. the ten Stoic themes
    └── gosai_bangla.md
```

The three layers form a chain: a **reference** (raw text) is analyzed into a **quality** (seed analysis), which yields a **theme set** (philosophical lens). Each layer is cataloged by its own `registry.md`.

---

## References (`.space/context/references/`)

A **reference** is a raw source text — the material the writer agent reads for direct stylistic and thematic grounding. It is the *input*, never the analysis.

### What a reference file is

- **One file = one work.** Each file holds a single source text (a book, a dictionary, a corpus).
- **Read-only input.** The writer agent reads references; it never modifies them.
- **Format is flexible.** Plain text (`.txt`) is the norm, but any readable format works. The registry records the format.
- **Language is recorded.** A reference may be in any language; the registry notes it.

### The reference registry (`registry.md`)

Every reference must be cataloged in `references/registry.md`. The registry has:

1. **A table** — one row per reference: file, work, author, format, language, status.
2. **A detail section** — one block per reference with work, author, translation, format, language, structure, and links to its associated quality and themes.
3. **An "add a new reference" procedure** — the steps to register a new source.

### Example — `aurilus.txt`

```
# Reference Registry
| # | Reference File | Work | Author | Format | Language | Status |
| 1 | aurilus.txt | The Meditations | Marcus Aurelius | Plain text (full text) | English | ✅ Active |
```

The detail block records the translation (Jeremy Collier, revised by Alice Zimmern, 1887), the structure (12 Books of aphorisms), and cross-links to `../qualities/aurilus.md` and `../themes/generic.md`.

### Adding a reference

1. Add the source text file to `context/references/` (e.g. `rumi_masnavi.txt`).
2. Add a row to the registry table and a detail section below.
3. Create a matching quality file in `context/qualities/` (the analysis of the reference).
4. Create a matching theme set in `context/themes/` if the reference introduces new themes.
5. Point a book instance at the new reference.

---

## Qualities (`.space/context/qualities/`)

A **quality** is the *seed analysis* of a reference work — the philosophical framework, metaphor families, quality metrics, and thematic grounding that the writer agent uses to render chapters in the target voice. It is the *analysis*, not the source text.

### What a quality file is

- **One quality = one reference book.** Each file analyzes a single source text.
- **Read-only input.** The writer agent reads qualities; it never modifies them.
- **The analysis is structured.** A quality file follows a fixed section layout (see below).
- **Themes and references live separately.** A quality links to its theme set and reference; it does not embed them.

### The quality file structure

A quality file (e.g. `aurilus.md`) follows this canonical layout:

1. **Document Overview** — source file, work, genre, structure.
2. **Quality Metrics Analysis** — rated dimensions, each with characteristics:
   - Philosophical Depth
   - Metaphorical Richness
   - Human Accessibility
   - Civilizational Relevance
   - Literary Quality
   - Ethical Framework
3. **Metaphorical Landscape** — dominant metaphor families (e.g. Nature, Theatrical, Architectural, Fire, Body), each with purpose and examples.
4. **Philosophical Innovations** — the core ideas the work contributes.
5. **Relevance Patterns** — how the work maps to the target voice.
6. **Linguistic/Stylistic DNA** — register, cadence, lexicon.
7. **Quality Assessment Summary** — an overall rating.
8. **Recommendations** — seed topics for the writer.

### The quality registry (`registry.md`)

Every quality must be cataloged in `qualities/registry.md`. The registry has:

1. **A table** — one row per quality: file, reference work, author, genre, language, status.
2. **A detail section** — one block per quality with the reference work, author, genre, structure, core themes, metaphor families, quality ratings, and links to its theme set and index.
3. **An "add a new quality" procedure** — the steps to register a new analysis.

### Example — `aurilus.md`

The analysis of *The Meditations* records:

- **Core philosophical themes:** Virtue as Sole Good, Cosmopolitanism, Transience, Divine Reason (Logos), Self-Governance, Acceptance of Fate (amor fati).
- **Dominant metaphor families:** Nature, Theatrical/Performance, Architectural/Structural, Fire/Element, Body/Medical.
- **Quality ratings:** Philosophical Depth 9.5/10, Metaphorical Richness 8.5/10, Human Accessibility 9/10, Civilizational Relevance 10/10, Literary Quality 7.5/10, Ethical Framework 9/10 — **Overall 9.2/10**.

### Adding a quality

1. Create a new seed analysis file in `context/qualities/` (e.g. `rumi.md`, `tagore.md`).
2. Follow the canonical structure above.
3. Add a row to the registry table and a detail section below.
4. Create a matching theme set in `context/themes/` if the quality introduces new themes.
5. Point a book instance at the new quality file.

---

## The Reference → Quality → Theme Chain

The three layers are linked, not independent:

```
reference (raw text)  →  quality (analysis)  →  theme set (lens)
aurilus.txt           →  aurilus.md          →  generic.md
gosai_dictionary.txt  →  (analysis)          →  gosai_bangla.md
```

- A **reference** is the raw source text (e.g. the full text of *The Meditations*).
- A **quality** is the *analysis* of that text — its voice, metaphor families, and quality metrics.
- A **theme set** is the *philosophical lens* derived from the analysis — the categories the writer cycles through.

When you add a reference, you must also add its quality (the analysis) and, if it introduces new themes, its theme set. Keep the three registries in sync.

---

## Per-Chapter Research

Beyond the shared context folder, research also produces **per-chapter research files** — one JSON per chapter, grounded in the book's chapter plan. This is the material the writer agent draws on when writing each chapter.

### Input: the book plan

1. Read `.space/pipeline/<bookname>/book.json`.
2. If `book.json` is absent, read `.space/pipeline/<bookname>/model.json` instead.
3. From it, extract the **chapter list** — each chapter's `chapter_index`, `name`, `chapter_title`, and `chapter_summary`.

The chapter summaries are the seed for research: each summary tells you what the chapter is about, so you know what to research for it.

### Output: one JSON per chapter

For each chapter, write a research file to:

```
.space/pipeline/<bookname>/chapters_research/<n>.json
```

where `<n>` is the chapter index (e.g. `1.json`, `2.json`, … `20.json`). One file per chapter, named by its index.

### The per-chapter research file structure

Each `<n>.json` should be structured so the writer can draw on it directly. At minimum:

```json
{
  "chapter_index": 1,
  "chapter_title": "The Dawn of Consciousness",
  "chapter_summary": "…",
  "era": "…",
  "place": "…",
  "key_figures": ["…"],
  "key_events": ["…"],
  "material_culture": ["…"],
  "social_structure": "…",
  "themes": ["…"],
  "sources": ["…"]
}
```

- **`chapter_index`** — the chapter number, matching `book.json`.
- **`chapter_title`** and **`chapter_summary`** — copied from the book plan, so the file is self-contained.
- **`era`** and **`place`** — the time and setting the chapter covers.
- **`key_figures`** and **`key_events`** — the people and turning points relevant to the chapter.
- **`material_culture`** — clothing, food, tools, art, and other concrete detail.
- **`social_structure`** — class, law, religion, custom.
- **`themes`** — the thematic categories the chapter should embody (from the book's theme set).
- **`sources`** — where each fact came from, so it is traceable.

### Method

1. **Read the book plan** — `book.json` (or `model.json` if absent).
2. **For each chapter**, read its `chapter_summary` and identify what needs research: an era, a place, a figure, an event, a subject.
3. **Gather and verify** — use the internet, provided texts, and the context folder; cross-check and flag uncertainty.
4. **Write `<n>.json`** to `chapters_research/`, one file per chapter, following the structure above.
5. **Keep it actionable** — the writer must be able to turn each fact into scene, dialogue, and sensory detail.

### Rules

- **One file per chapter**, named by chapter index (`<n>.json`).
- **Grounded in the chapter summary** — research only what the chapter is about.
- **Traceable** — every fact carries a source note.
- **Actionable** — facts serve the story; they are not a lecture.
