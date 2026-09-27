# Syntax Registry

A catalog of every syntax sample available in `stereotypes/poetry/syntax/`. Each syntax file defines the target sentence structure — the register, sentence patterns, and readability bar that keep the language current while preserving an elevated cadence.

The syntax agent reads this registry to discover available syntax samples, then reads the chosen sample file for the full definition.

---

## Available Syntax Samples

| # | Syntax File | Source | Register | Status |
|---|-----------|--------|----------|--------|
| 1 | [`generic.md`](generic.md) | Marcus Aurelius — *The Meditations* (Stoic/prophetic) | Archaic/literary, long flowing sentences | ✅ Active |
| 2 | [`gosai_bangla.md`](gosai_bangla.md) | Baul-Fakir tradition (Gosai lexicon) | Archaic/literary, songlike and wandering | ✅ Active |

---

## Syntax Sample Details

### 1. `generic.md` — The Default (Stoic/Prophetic) Syntax

- **Source:** Marcus Aurelius's *Meditations*, rendered in the prophetic register
- **Register:** Archaic/literary
- **Sentence pattern:** Long, flowing sentences that unfold through clauses, images, and emotional turns; commas, semicolons, and dashes create a controlled current of thought
- **Associated Theme Set:** [`../themes/generic.md`](../themes/generic.md) — the ten Stoic themes
- **Associated Reference:** [`../references/aurilus.txt`](../references/aurilus.txt)

### 2. `gosai_bangla.md` — The Baul-Fakir Syntax

- **Source:** Gosai/Baul/Fakir spiritual tradition (from `../references/gosai_dictionary.txt`)
- **Register:** Archaic/literary with songlike, meditative cadence
- **Sentence pattern:** Wandering, incantatory, and intimate; repetition and refrain carry the seeker's movement
- **Associated Theme Set:** [`../themes/gosai_bangla.md`](../themes/gosai_bangla.md) — the ten Baul-Fakir themes

---

## How to Add a New Syntax Sample

1. Create a new syntax file in `stereotypes/poetry/syntax/` (e.g. `rumi.md`, `tagore.md`).
2. Add a row to the table above and a detail section below.
3. Sync the master index at `../registry.md`.

---

## Conventions

- **One syntax sample = one sentence philosophy.** Each file defines a distinct register and sentence pattern.
- **Syntax files are read-only inputs.** The writers and syntax agents read them; they never modify them.
- **Syntax must match the theme set.** The sentence structure and the philosophical lens belong to the same source or tradition so the poem reads as a coherent whole.
