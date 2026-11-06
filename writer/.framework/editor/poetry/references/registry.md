# Reference Registry (Poetry)

A catalog of every reference source available in `.framework/editor/poetry/references/`.
Each reference is a **source text or note set** — the raw material the writer/research
agents read for direct stylistic and thematic grounding. A reference supplies the *what*;
it never fixes meter (that is a style) and never defines a voice (that is a signature).

The research/correctness filters and the writing agents read this registry to discover
available sources, then read the individual file for the material itself.

---

## Available References

| # | Folder | File(s) | Work / Source | Notes | Status |
|---|--------|---------|---------------|-------|--------|
| 1 | `philophical/` | `aurilus.txt` | *The Meditations* — Marcus Aurelius | Full source text; paired with `themes/aurilus/theme.md` (seed analysis) | ✅ Active |
| 2 | `philophical/` | `languages_sample.txt` | "The Right of the Flower" — framework sample | Prophetic-register prose sample for calibration | ✅ Active |
| 3 | `gosai/` | `gosai_dictionary.txt` | *Gosai: Prose of Leaving Home* — Baul/Fakir lexicon | Paired with `themes/gosai_bangla/theme.md` + `syntax/gosai_bangla/syntax.md` | ✅ Active |
| 4 | `srijato/` | `analysis.md`, `writesup.md` | Srijato Bandyopadhyay — reference notes | Poem-structure/rhyme/syllable-signature notes for the srijato voice | ✅ Active |
| 5 | `research/` | `checklist.md`, `example_all_time.md`, `Postmodern.md`, `text200bc-2020ad.md` | Style-slider research notes | Grounding for the `poetry-slider.json` movement parameters | ✅ Active |
| 6 | `najrul/` | *(empty)* | Kazi Nazrul Islam — reserved | Placeholder; no source text yet staged | ⚪ Reserved |
| 7 | `tagore/` | *(empty)* | Rabindranath Tagore — reserved | Placeholder; no source text yet staged | ⚪ Reserved |

---

## Conventions

- **One reference = one source work or note set.** Each entry is the raw material,
  not an analysis and not a rule.
- **References are distinct from themes.** A theme set (`themes/<x>/theme.md`) is the
  *philosophical lens / seed analysis* derived from a reference; the reference is the
  source text itself.
- **References are distinct from signatures.** A signature (`signatures/<x>/`) is a
  poet's *voice*; a reference is the source material a writer draws on.
- **Reference files are read-only inputs.** The writer/research agents read them; they
  never modify them.
- **Empty folders are reserved.** `najrul/` and `tagore/` are placeholders awaiting
  source material; do not treat their emptiness as a defect.
