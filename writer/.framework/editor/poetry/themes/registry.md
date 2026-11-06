# Theme Registry (Poetry)

A catalog of every theme set available in `.framework/editor/poetry/themes/`.
Each theme set defines the **philosophical lenses** that give chapters their spine, and
carries its **seed analysis** (quality metrics, metaphor families, creative parameters)
inside the same `theme.md` — there is no separate `qualities/` folder (see
`.framework/rules/style-signature-quality.md`).

The theme filter and the quality filter read this registry to discover available theme
sets, then read the chosen `theme.md` for both the lenses and the seed analysis.

---

## Available Theme Sets

| # | Folder | Source / Tradition | Theme Count | Carries seed analysis | Status |
|---|--------|--------------------|-------------|-----------------------|--------|
| 1 | `generic/` | Marcus Aurelius — *The Meditations* (Stoic) | 10 | ✅ (Stoic metrics + metaphor families) | ✅ Active |
| 2 | `gosai_bangla/` | Baul-Fakir tradition (Gosai lexicon) | 10 | ✅ (Moromi / মরমি register) | ✅ Active |
| 3 | `aurilus/` | Marcus Aurelius — *The Meditations* | — | ✅ **seed analysis only** (the canonical Meditations seed; its ten lenses live in `generic/`) | ✅ Active |

---

## Conventions

- **One theme set = one philosophical source.** Each `theme.md` derives its lenses (and
  its seed analysis) from a single reference work or tradition.
- **The seed analysis lives here.** Quality metrics, metaphor families, and creative
  parameters are carried inside the theme set's `theme.md` — the content bar the quality
  filter audits against. Never pull them from a `style.md`.
- **Theme files are read-only inputs.** The theme/quality agents read them; they never
  modify them.
- **`aurilus/` is the seed-analysis home.** It holds the canonical Meditations seed
  analysis; the ten derived lenses are in `generic/`. `gosai_bangla/` fuses both.
- **Cycle in order.** The writer assigns themes by cycling the list (1 → N → 1) so no
  lens dominates.
