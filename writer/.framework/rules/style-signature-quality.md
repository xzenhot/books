# Style / Signature / Quality — Layer Separation

The poetic context under `.framework/editor/<form>/` is split into **three
non-overlapping layers**. Each owns one kind of knowledge; mixing them is a
defect. This rule is the authoritative boundary for `styles/`, `signatures/`, and
`themes/` (which carries the seed analysis / quality) in both `novel/` and
`poetry/`.

## The Three Layers

| Layer | Folder | Owns | Never owns |
|---|---|---|---|
| **Style** | `styles/<style>/` | **Structure only** — syntax, meter/syllables, line/stanza shape, caesura, rhyme scheme, register. The *how the text is shaped*. | Persona, imagery, emotional directives, metaphor families, "what to feel", creative content. |
| **Signature** | `signatures/<poet>/` | **The voice** — a poet's characteristic *movement, motifs, diction, pattern*. The *who is speaking*. | Line-count rules, meter, rhyme contracts, content generation, theme assignment. |
| **Theme / Seed analysis (the quality)** | `themes/<theme-set>/` | **The content bar** — a seed analysis of a reference work: philosophical depth, metaphor families, quality metrics, and the `creative_enrichment` profile (image_seed, volta, sonic_texture, line_gesture, metaphor_family, closing_move, address). The *what to generate and how deep*. | Syntax, meter, line structure, register rules, poet-voice identity. |

There is **no separate `qualities/` folder**. The seed-analysis / quality content
lives inside `themes/<theme-set>/theme.md` — one theme set carries both its ten
thematic lenses and its seed analysis (metrics, metaphor families, creative
parameters).

## The Contract (binding)

1. **Style = structure.** A `style.md` may state *how* a line is built (its
   syllable/akshar count, its stanza shape, its rhyme scheme, its register) — and
   nothing about *what* to imagine or *how* to feel. Persona paragraphs, "Required
   Writing Principles" that are really mood/imagery directives, and "Good Anchors"
   that are content are **out of layer** and belong in a signature or quality.
2. **Signature = voice.** A `signature.md` states the poet's movement, motifs,
   diction, and pattern. It never fixes a meter or rhyme contract (that is style's
   job) and never assigns themes or generates content (that is quality's job).
3. **Theme / Seed analysis = content.** A theme set's `theme.md` states the
   reference work's philosophical depth, metaphor families, quality metrics, and
   creative-enrichment parameters. It is the seed for *what* the writer generates
   — never the structural ruler.
4. **Fixed forms are style-bound.** A metred form (`poyar`, `amitra`, `srijato`,
   `sonnet`, `haiku`, `limerick`, `lyrics`) is a **style**, not a voice and not a
   content source. Its `style.md` owns the meter/rhyme contract; the *content*
   still comes from the book's theme set (seed analysis) and the *voice* from its
   signature.
5. **The creative content belongs in themes.** `creative_enrichment`
   (`image_seed`, `volta`, `sonic_texture`, `line_gesture`, `metaphor_family`,
   `closing_move`, `address`, `variety_note`) is content-generation knowledge and
   lives in the theme set's seed analysis — never inside a `style.md`.

## Resolution Order (the writer/enrich/quality agents)

```
chapter model (base)
  → signature (voice: movement, motif, diction, pattern)
  → style (structure: syntax, meter, line/stanza, rhyme, register)
  → theme set / seed analysis (content: metrics, metaphor families, creative_enrichment)
  → override (human mandate, final and binding)
```

No layer may supply another layer's knowledge. A style that smuggles creative
content is re-grounded or retired; a signature that fixes meter is folded into a
style; a theme set that fixes syntax is moved to a style.

## Migration Consequences

- **POV/tonal `styles/`** (descriptive, dark, lyrical, expository, persuasive,
  narrative, omniscient, first-person, …) are **register/voice**, not structure.
  Their persona and creative directives are **folded into signatures** (or theme
  sets); any structural residue (line shape, register) is kept as the style's one
  legitimate line.
- **Structural `styles/`** (`poyar`, `amitra`, `srijato`, and other metred forms)
  are stripped of persona/imagery and reduced to the meter + register contract.
- **`signatures/`** gains a `registry.md`; poet-voice identity is normalized there,
  and any meter/rhyme clauses are moved out to the owning style.
- **`themes/<theme-set>/theme.md`** carries the seed analysis (quality metrics,
  metaphor families, `creative_enrichment`) alongside its ten thematic lenses — no
  separate `qualities/` folder. The quality filter reads the theme set's
  `theme.md` as the content bar.

## Audit

The eval-judge completeness pass checks this boundary: a `style.md` carrying
persona/metaphor/emotional directives is a defect; a `signature.md` fixing a
meter is a defect; a `theme.md` seed analysis that is empty or that fixes syntax
is a defect.