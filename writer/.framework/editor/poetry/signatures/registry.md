# Signature Registry (Poetry)

A catalog of every poetic signature available in `.framework/editor/poetry/signatures/`.
Each signature is a distinct **poet-voice** — a writer's characteristic movement,
motifs, diction, and pattern — that the enrich and theme agents use to give a poem
its voice. A signature supplies the *who is speaking*; it never fixes meter or
rhyme (that is the style's job) and never assigns themes or generates content (that
is the quality's job).

The enrich-poetry and theme-poetry skills read this registry to discover available
signatures, then read the individual `signature.md` for the full definition.

---

## Available Signatures

| # | Signature | Poet | Movement | Status |
|---|-----------|------|----------|--------|
| 1 | `aurilus` | Marcus Aurelius | Meditative, restrained, Stoic | ✅ Active |
| 2 | `blake` | William Blake | Visionary, prophetic, mythic | ✅ Active |
| 3 | `dickinson` | Emily Dickinson | Compressed, elliptical, interior | ✅ Active |
| 4 | `eliot` | T. S. Eliot | Fragmentary, allusive, collage | ✅ Active |
| 5 | `gibran` | Kahlil Gibran | Biblical, aphoristic, oracular | ✅ Active |
| 6 | `hafez` | Hafez | Ecstatic, wine-lit, paradoxical | ✅ Active |
| 7 | `jibanananda` | Jibanananda Das | Twilight-toned, solitary, sensuous | ✅ Active |
| 8 | `lorca` | Federico García Lorca | Duende, moonlit, blood-rooted | ✅ Active |
| 9 | `nazrul` | Kazi Nazrul Islam | Rebellious, fiery, musical | ✅ Active |
| 10 | `neruda` | Pablo Neruda | Sensuous, cataloguing, elegiac | ✅ Active |
| 11 | `rabindranath` | Rabindranath Tagore | Lyrical, devotional, universal | ✅ Active |
| 12 | `rabindrasangeet` | Rabindranath Tagore (song) | Songlike, devotional, intimate | ✅ Active |
| 13 | `rilke` | Rainer Maria Rilke | Elegiac, angelic, contemplative | ✅ Active |
| 14 | `rumi` | Rumi | Longing-into-union, ecstatic | ✅ Active |
| 15 | `shakti` | Shakti Chattopadhyay | Whimsical, existential, colloquial | ✅ Active |
| 16 | `sukanta` | Sukanta Bhattacharya | Revolutionary, stark, urgent | ✅ Active |
| 17 | `whitman` | Walt Whitman | Expansive, cataloguing, democratic | ✅ Active |
| 18 | `yeats` | W. B. Yeats | Mythic, symbolic, ceremonial | ✅ Active |
| 19 | `aurilus-rumi-eliot-gibran` | (compound) | Stoic + ecstatic + fragmentary + oracular | ✅ Active |

---

## How to Add a New Signature

1. Create a folder `.framework/editor/poetry/signatures/<name>/`.
2. Write `signature.md` with four sections: **Core Movement**, **Motifs**,
   **Diction**, **Pattern** (optionally a **Sample**).
3. Add a row to the table above and a detail section below.

---

## Conventions

- **One signature = one poet-voice.** Each file defines a single voice's movement,
  motif, and music.
- **Signatures own the voice, not the structure, not the content.** Meter, rhyme,
  and line shape belong to `styles/`; philosophical depth, metaphor families, and
  creative parameters belong to the theme set's seed analysis
  (`themes/<theme-set>/theme.md`). See `.framework/rules/style-signature-quality.md`.
- **Signature files are read-only inputs.** The writer/enrich agents read them; they
  never modify them.
- **Compound signatures** are named with hyphens (e.g. `aurilus-rumi-eliot-gibran`)
  and describe one blended voice, not several poems.
---

## Folded Tonal/POV Voices (from retired `styles/`)

These voices were originally `styles/` "transmuters". Under
`.framework/rules/style-signature-quality.md` they are **voices, not structure**,
so they now live here. Each carries the same persona/diction/motif content; their
structural residue (if any) was dropped with the style folder.

| # | Signature | Voice | Status |
|---|-----------|-------|--------|
| 20 | `action-packed` | The Kinetic — high-velocity, staccato, movement-first | ✅ Active |
| 21 | `dark` | The Keeper of the Unlit — grave, unflinching, shadow-honest | ✅ Active |
| 22 | `descriptive` | The Observer — sensory fullness, the scene made vivid | ✅ Active |
| 23 | `dialogue-driven` | The Conversationalist — talk as the engine | ✅ Active |
| 24 | `epistolary` | The Correspondent — letters, intimacy, address | ✅ Active |
| 25 | `experimental` | The Formalist-in-reverse — broken form, collage | ✅ Active |
| 26 | `expository` | The Clarifier — plain, ordered explanation | ✅ Active |
| 27 | `first-person` | The Confessor — the "I" as witness | ✅ Active |
| 28 | `humorous` | The Wit — wry, deadpan, warm comedy | ✅ Active |
| 29 | `interactive` | The Addresser — direct engagement with the reader | ✅ Active |
| 30 | `lyrical` | The Singer of Prose — cadence and image | ✅ Active |
| 31 | `minimalist` | The Editor of the Essential — spare, exact, quiet | ✅ Active |
| 32 | `narrative` | The Teller — story, sequence, momentum | ✅ Active |
| 33 | `persuasive` | The Advocate — argument that moves | ✅ Active |
| 34 | `philosophical` | The Inquirer — the question pressed to depth | ✅ Active |
| 35 | `reflective` | The Meditator — the experience turned over in thought | ✅ Active |
| 36 | `satirical` | The Ironist — the deadpan that exposes folly | ✅ Active |
| 37 | `stream-of-consciousness` | The Inner Flow — thought as it happens | ✅ Active |
| 38 | `third-person-limited` | The Focused Narrator — one mind, held close | ✅ Active |
| 39 | `unreliable-narrator` | The Doubter — a voice the reader learns to distrust | ✅ Active |
| 40 | `vignette` | The Snapshot — a single held moment | ✅ Active |
