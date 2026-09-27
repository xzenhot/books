# Poetry Stereotype Registry — Master Index

A catalog of the complete `poetry/` stereotype folder and all its subfolders. This registry is the top-level index; each subfolder owns a dedicated `registry.md` that catalogs its own contents in detail.

The writer/theme/syntax agents read the relevant **sub-registry** to discover options, then read the chosen file for the full definition. This master index tells them where to look.

---

## Folder Map

```text
poetry/
|-- registry.md            # this master index
|-- default/               # a complete default book instance (seed book)
|-- qualities/             # seed analyses: one per reference work
|-- references/            # raw source texts: one file per work
|-- signatures/            # poetic voices: one folder per signature
|-- syntax/                # syntax samples: target sentence structures
`-- themes/                # theme sets: philosophical lenses
```

## Summary

| Subfolder | Contents | Local registry | Status |
|---|---|---|---|
| `default/` | A complete default poetry book instance (seed → config → chapters) | — | ✅ Active |
| `qualities/` | 1 quality: `aurilus.md` | [`qualities/registry.md`](qualities/registry.md) | ✅ Active |
| `references/` | 3 reference texts: `aurilus.txt`, `gosai_dictionary.txt`, `languages_sample.txt` | [`references/registry.md`](references/registry.md) | ✅ Active |
| `signatures/` | 18 signatures, one folder each with a `signature.md` | [`signatures/registry.md`](signatures/registry.md) | ✅ Active |
| `syntax/` | 2 syntax samples: `generic.md`, `gosai_bangla.md` | [`syntax/registry.md`](syntax/registry.md) | ✅ Active |
| `themes/` | 2 theme sets: `generic.md`, `gosai_bangla.md` | [`themes/registry.md`](themes/registry.md) | ✅ Active |

---

## 1. `default/` — The Default Book Instance

A ready-made poetry pipeline template (the "seed book") used as the source shape for a new poetry pipeline. All files are structural inputs; the chapters are sample outputs.

| File / Folder | Purpose |
|---|---|
| [`config.json`](default/config.json) | Book configuration: title, language, register, quality/themes/reference paths, index, sacred vocabulary, translation guide |
| [`writer.md`](default/writer.md) | Book-specific instance of the writer agent wiring the seed inputs together |
| [`bookseed.txt`](default/bookseed.txt) | The topic index: one term per line (each term becomes one chapter) |
| [`override.md`](default/override.md) | Seed-book sample of an override transformation layer — note: in an actual pipeline the operative override command file is `filters/override/filter.md`, **not** a pipeline-root file |
| [`progress.json`](default/progress.json) | Progress tracking shape (one entry per topic) |
| [`ai_studio_code1.json`](default/ai_studio_code1.json) | Optional AI-studio seed code: topic, category, idea, opening/closing story |
| [`chapters/`](default/chapters/) | 5 sample finished chapters: `Chapter_001_Gravity.md` … `Chapter_005_Equilibrium.md` |

**Example seed book:** *The Invisible Law — A Prophet of Science and Soul* — physics/science terms rendered in a Gibran-esque voice, grounded in Marcus Aurelius's *Meditations* (Stoic themes).

---

## 2. `qualities/` — Seed Analyses

Each quality is the **analysis of one reference work**: philosophical framework, metaphor families, quality metrics, and thematic grounding.

| # | File | Reference work | Author | Genre | Status |
|---|---|---|---|---|---|
| 1 | [`aurilus.md`](qualities/aurilus.md) | *The Meditations* | Marcus Aurelius | Stoic Philosophy / Personal Reflections | ✅ Active |

Full details: [`qualities/registry.md`](qualities/registry.md)

---

## 3. `references/` — Source Texts

Each reference is the **raw source text** the writer reads for direct stylistic and thematic grounding.

| # | File | Content | Language | Status |
|---|---|---|---|---|
| 1 | [`aurilus.txt`](references/aurilus.txt) | *The Meditations* of Marcus Aurelius (full text) | English | ✅ Active |
| 2 | [`gosai_dictionary.txt`](references/gosai_dictionary.txt) | The Gosai/Baul/Fakir spiritual lexicon — "Prose of Leaving Home" | English | ✅ Active |
| 3 | [`languages_sample.txt`](references/languages_sample.txt) | A philosophical prose sample on rights/nature in the prophetic register | English | ✅ Active |

Full details: [`references/registry.md`](references/registry.md)

---

## 4. `signatures/` — Poetic Voices

Each signature is a distinct poetic voice, stored in its own folder with a `signature.md` defining **Core Movement, Motifs, Diction, Pattern, Sample**.

| # | Signature | Folder | Voice | Status |
|---|---|---|---|---|
| 1 | Kahlil Gibran | [`gibran/`](signatures/gibran/signature.md) | Biblical, aphoristic, oracular | ✅ Active |
| 2 | Marcus Aurelius | [`aurilus/`](signatures/aurilus/signature.md) | Meditative, restrained, Stoic | ✅ Active |
| 3 | Jibanananda Das | [`jibanananda/`](signatures/jibanananda/signature.md) | Twilight-toned, solitary, sensuous | ✅ Active |
| 4 | Rabindranath Tagore (Sangeet) | [`rabindrasangeet/`](signatures/rabindrasangeet/signature.md) | Songlike, devotional, intimate | ✅ Active |
| 5 | Rumi | [`rumi/`](signatures/rumi/signature.md) | Ecstatic, mystical, intoxicated | ✅ Active |
| 6 | Walt Whitman | [`whitman/`](signatures/whitman/signature.md) | Expansive, democratic, celebratory | ✅ Active |
| 7 | Emily Dickinson | [`dickinson/`](signatures/dickinson/signature.md) | Compressed, elliptical, startling | ✅ Active |
| 8 | Pablo Neruda | [`neruda/`](signatures/neruda/signature.md) | Sensuous, elemental, overflowing | ✅ Active |
| 9 | Rainer Maria Rilke | [`rilke/`](signatures/rilke/signature.md) | Inward, solitary, reverent | ✅ Active |
| 10 | William Blake | [`blake/`](signatures/blake/signature.md) | Visionary, prophetic, mythic | ✅ Active |
| 11 | Federico García Lorca | [`lorca/`](signatures/lorca/signature.md) | Duende-filled, tragic, Andalusian | ✅ Active |
| 12 | W. B. Yeats | [`yeats/`](signatures/yeats/signature.md) | Mythic, musical, time-haunted | ✅ Active |
| 13 | T. S. Eliot | [`eliot/`](signatures/eliot/signature.md) | Fragmented, allusive, modern | ✅ Active |
| 14 | Hafez | [`hafez/`](signatures/hafez/signature.md) | Intoxicated, playful, wise | ✅ Active |
| 15 | Kazi Nazrul Islam | [`nazrul/`](signatures/nazrul/signature.md) | Fiery, rebellious, ecstatic | ✅ Active |
| 16 | Rabindranath Tagore | [`rabindranath/`](signatures/rabindranath/signature.md) | Songlike, devotional, wonder-filled | ✅ Active |
| 17 | Sukanta Bhattacharya | [`sukanta/`](signatures/sukanta/signature.md) | Urgent, revolutionary, hungry for justice | ✅ Active |
| 18 | Shakti Chattopadhyay | [`shakti/`](signatures/shakti/signature.md) | Bohemian, wandering, tenderly ironic | ✅ Active |

Full details: [`signatures/registry.md`](signatures/registry.md)

---

## 5. `syntax/` — Syntax Samples

Each syntax file defines the target sentence structure: register, sentence patterns, and the readability bar.

| # | File | Content | Status |
|---|---|---|---|
| 1 | [`generic.md`](syntax/generic.md) | The default (Stoic/prophetic) syntax — long flowing sentences, archaic/literary register | ✅ Active |
| 2 | [`gosai_bangla.md`](syntax/gosai_bangla.md) | The Baul-Fakir adaptation of the prophetic syntax — songlike, wandering, incantatory cadence | ✅ Active |

Full details: [`syntax/registry.md`](syntax/registry.md)

---

## 6. `themes/` — Theme Sets

Each theme set is a **philosophical lens** derived from a source, giving each chapter its spine.

| # | File | Source | Theme count | Language | Status |
|---|---|---|---|---|---|
| 1 | [`generic.md`](themes/generic.md) | Marcus Aurelius — *The Meditations* | 10 | Target language | ✅ Active |
| 2 | [`gosai_bangla.md`](themes/gosai_bangla.md) | Baul-Fakir tradition (Gosai lexicon) | 10 | Target language | ✅ Active |

Full details: [`themes/registry.md`](themes/registry.md)

---

## How to Use

1. **Pick the form folder.** For poetry, use `poetry/`. For novels, use `novel/` (same shape; different signature set).
2. **Consult the sub-registry.** Each subfolder's `registry.md` catalogs its files with the exact columns agents read.
3. **Select consistently.** The theme/syntax agents select a signature, reference, theme set, and syntax sample from the same form, and where possible the same author or tradition, so a chapter reads as a coherent whole.
4. **Read the chosen file.** Registries only point; the chosen file holds the full definition.

## How to Add Content

1. Add the new file/folder in the matching subfolder.
2. Update that subfolder's `registry.md` (table + detail section).
3. Update the relevant table in this master index (counts + row).

## Conventions

- **One reference = one source text.** `references/` holds raw text; `qualities/` holds the analysis of it; `themes/` holds the lens derived from it.
- **Registry files are catalogs.** They never contain the definitions themselves — only pointers.
- **Selections must be mutually consistent.** Same form, and where possible the same author or tradition.
