# Theme Registry

A catalog of every thematic category set available in `stereotypes/novel/themes/`. Each theme file defines the philosophical lenses that give chapters their spine — the categories the writer agent cycles through when assigning a lens to each chapter.

The writer agent reads this registry to discover available theme sets, then reads the individual theme file for the full definitions.

---

## Available Theme Sets

| # | Theme File | Source | Theme Count | Language | Status |
|---|-----------|--------|-------------|----------|--------|
| 1 | [`generic.md`](generic.md) | Marcus Aurelius — *The Meditations* (Stoic) | 10 | Target language | ✅ Active |
| 2 | [`gosai_bangla.md`](gosai_bangla.md) | Baul-Fakir tradition (Gosai lexicon) | 10 | Target language | ✅ Active |

---

## Theme Set Details

### 1. `generic.md` — The Ten Stoic Themes

- **Source:** Marcus Aurelius's *Meditations* (Stoic philosophy)
- **Theme Count:** 10
- **Language:** Target language — archaic/literary register
- **Associated Quality:** [`../qualities/aurilus.md`](../qualities/aurilus.md)
- **Associated Reference:** [`../references/aurilus.txt`](../references/aurilus.txt)

**The Ten Themes:**

| # | Theme | Essence | Notes |
|---|-------|---------|-------|
| 1 | The Inner Citadel | Withdrawal into the self as an unbreachable refuge | Use the target-language equivalent at generation time. |
| 2 | The One Blood | Universal kinship; all beings as limbs of one body | Use the target-language equivalent at generation time. |
| 3 | The Fading Name | Indifference to fame; the vanity of reputation | Use the target-language equivalent at generation time. |
| 4 | The Only Present | The eternal now; past and future as ghosts | Use the target-language equivalent at generation time. |
| 5 | The Beloved Necessity | Amor fati — loving one's fate | Use the target-language equivalent at generation time. |
| 6 | The Last Change | Death as transformation, not ending | Use the target-language equivalent at generation time. |
| 7 | The Royal Service | Service as the highest nobility | Use the target-language equivalent at generation time. |
| 8 | The Uncluttered Soul | Simplicity and detachment | Use the target-language equivalent at generation time. |
| 9 | The Woven Whole | The unity of all things | Use the target-language equivalent at generation time. |
| 10 | The Undefeated Virtue | Virtue's invincibility | Use the target-language equivalent at generation time. |

Each theme in `generic.md` provides: **essence**, **Stoic source** (the grounding quote), **prophetic transformation** (how to render it), **metaphor family** (imagery to draw from), **seed phrases**, and a **sample opening** (a ready-made "The Question" line).

### 2. `gosai_bangla.md` — The Ten Baul-Fakir Themes

- **Source:** Gosai/Baul/Fakir spiritual tradition (from `../references/gosai_dictionary.txt`)
- **Theme Count:** 10
- **Language:** Target language — archaic/literary register
- **Associated Syntax:** [`../syntax/gosai_bangla.md`](../syntax/gosai_bangla.md)

The same ten Stoic categories re-imagined through the Baul-Fakir lens — the inner shrine of the Beloved, one blood flowing through every person, the person of the heart, the unburdened soul. Each theme provides: **essence**, **metaphor family**, **sacred words**, and **Baul-Fakir resonance**.

---

## How to Add a New Theme Set

1. Create a new theme file in `stereotypes/novel/themes/` (e.g. `rumi.md`, `tagore.md`, `nietzsche.md`).
2. Follow the same structure as `generic.md`:
   - A title and one-line description
   - A numbered list of themes, each with **Essence**, **Source**, **Transformation**, **Metaphor Family**, **Sacred Words**, and **Sample Opening**
   - A "Usage Notes" section (cycling, weaving, grounding, one-theme-per-chapter)
3. Add a row to the table above and a detail section below.
4. Sync the master index at `../registry.md`.

---

## Conventions

- **One theme set = one philosophical source.** Each file derives its themes from a single reference work or tradition.
- **Theme files are read-only inputs.** The writer agent reads them; it never modifies them.
- **Themes are distinct from qualities.** A quality defines *how* to write (voice, metaphor families, quality metrics); a theme set defines *what lens* to apply to each chapter.
- **Cycle in order.** The writer assigns themes by cycling through the list (1 → N → 1) so no theme dominates.
