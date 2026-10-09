# Enrich Poetry — Fuse the Active Filters (Poetic Pass)

You enrich a **poetry** pipeline's chapters. You do not apply filters yourself. Instead, you:

1. Read the active filter list from `filters.json`.
2. Fuse the active filter skills into **one combined pass**.
3. Execute that combined pass over each target poem's metadata.
4. Record the enrichment result — a `chapter.json` annotated `enriched` and ready for the
   write/poet agents to compose `chapter.md`. (You never author prose yourself.)

## Form

This skill applies to the **poetry** form only. The poetry filter chain is
`workshop → research → correctness → theme → syntax → override → quality`, one
segment (`segments/1`) per topic, and a 500–800 word target per poem.

## The Poetic Enrichment Model (this is what you record)

The enrichment you produce is **poetic**, not narrative. You are not inventing a story,
characters, or a plot; you are sharpening the **craft attributes** a poet needs before
composing a single poem. Every record you add must be traceable to the poem's own
`chapter.json` (`chapter_title`, `chapter_summary`, topic, and any prior guidance), and
must serve the poem — its image, its sound, its turn — never a prose arc.

## Inputs

1. `workspaces/pipeline/<bookname>/filters/filters.json` — the authoritative filter list.
2. `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` — the poem's metadata (the only per-chapter input).
3. The active filters' own outputs under `workspaces/pipeline/<bookname>/filters/<filter>/` — the fused guidance's source material.
4. `.framework/templates/stereotypes/poetry/signatures/<poet>/signature.md` — the poetic signatures (see *Poetic Signature*).
5. `.framework/templates/stereotypes/poetry/styles/<style>/` — the resolved style (see *Style Grounding*).

`chapter.md` is **not** an input here. It is an output file of the writing/authorship
path; you never read the poem's current prose. You do **not** read the backlog or the epic.

## Poetic Signature

Each poem is assigned a **poetic signature** — a poet-stereotype that gives the poem its
movement, motif, and music. The signatures live under
`.framework/templates/stereotypes/poetry/signatures/`:

```text
aurilus, blake, dickinson, eliot, gibran, hafez, jibanananda, lorca,
nazrul, neruda, rabindranath, rabindrasangeet, rilke, rumi, shakti,
sukanta, whitman, yeats,
aurilus-rumi-eliot-gibran   # the blended compound signature
```

Each `signature.md` defines four things you must fold into the poem's record:

- **Core Movement** — the poem's emotional/spatial gesture (e.g. Jibanananda's twilight
  solitude, Rumi's longing-into-union, Lorca's duende, Nazrul's rebellion, Whitman's
  expansive cataloguing).
- **Motifs** — the signature's recurring image set (e.g. Rumi's reed-flute and moth-flame;
  Yeats's swan/gyre/tower; Lorca's moon/guitar/blood).
- **Diction** — the register the signature demands.
- **Pattern** — the open → build → turn → close shape the signature follows.

Select a signature that suits the poem's topic; record it in the poem's `stereotype`
object (see *Output*). Do not force one signature onto every poem — vary across the book.

### The Mixed Signature — aurilus + rumi + eliot + gibran

When the poem calls for it, blend these four voices into **one compound signature**,
recorded as `"signature": "aurilus-rumi-eliot-gibran"`. It is not four poems; it is one
voice that borrows a single trait from each:

- **Aurelius (the ethical anchor)** — the calm inward turn, the moral reversal, the
  compact close: "name the human confusion, correct the scale, keep the ruling part clear."
  From this the poem takes its **stoic restraint** and its closing turn toward self-command.
- **Rumi (the ecstatic current)** — longing and union as one pole, the wound that opens
  into light, the dissolving self. From this the poem takes its **intoxicated lift** — the
  line that whirls upward instead of only weighing down.
- **Eliot (the fragmentary field)** — shored fragments, borrowed voices, register shifting
  from colloquial to liturgical, the objective correlative carrying feeling through image.
  From this the poem takes its **collage texture** and its refusal of smooth narrative.
- **Gibran (the oracular cadence)** — the seeker's question, the prophet's answer, the
  paradox, the circular benediction, the direct "you". From this the poem takes its
  **aphoristic, address-driven structure** and its final circular return.

**How they braid in a single poem:**

1. Open with an Eliot-style fragment or a Gibran-style address ("you", a question).
2. Let the Rumi current lift the image toward union or longing.
3. Ground it in an Aurelius moral reversal — the self made small, the duty made immense.
4. Close on a Gibran circular benediction that returns, transformed, to the opening image.

**Motifs to draw from (re-keyed to the book's material):** the inner citadel and the
fading name (Aurelius); the reed/flute, the moth and the flame, the wound-as-light
(Rumi); the dry stone, the wasteland, the fragment shored against ruin (Eliot); the seed,
the tide, the paradox, the cup-bearer (Gibran).

## Style Grounding

Resolve the book's style from `.framework/templates/stereotypes/poetry/styles/`:

- **desh** — the incantatory, collision-driven voice (see `styles/desh/style.md` and
  `signature.md`); re-key its imagery families to the book's own material.
- **pijush** — the Dehlij threshold-dweller voice (see `styles/pijush/style.md` and
  `signature.md`); ground the poem in a place and a body.

The style supplies the **voice**; the signature supplies the **movement and motif**. Keep
both consistent with the poem's topic — do not import a tantric/foreign lexicon onto a
poem that does not invite it.

## Poetic Parameters (what the fused pass records)

The enrichment is a **poetic parameter profile**, not a story outline. Load the
style-slider model from `.framework/templates/stereotypes/poetry/poetry-slider.json`
(the five `style_sliders`, the seven `movements` with their `parameter_weights`, and the
`writing_skills`). Record the poem's **parameters** — a set of numeric sliders plus the
movement and skills that shape it — inside the poem's `creative_enrichment` under a
`poetic_parameters` object.

### The five style sliders (scale 1–10)

Each slider names one axis of the poem's voice; assign a value per poem, and keep the
five consistent with each other (a high `emotional_rawness` with a low
`grammatical_abstraction` reads confessional, not language-poetry):

- `emotional_rawness` — objective philosophy → intense personal trauma/confession.
- `grammatical_abstraction` — clear narrative → broken syntax / abstract language play.
- `structural_rigidity` — organic free verse → strict formal constraint.
- `rhythmic_urgency` — silent reading → oral performance, musicality, pacing.
- `digital_simplicity` — dense lines → minimal vocabulary, short lines, screen-optimized.

### Movement & skills

- `movement` — the historical movement whose `parameter_weights` the poem's sliders
  align with (Stoicism, Sufism, Confessionalism, Language Poetry, New Formalism,
  Spoken Word, Instapoetry). Record the movement name and its one-liner.
- `writing_skills` — the movement's technique set (e.g. `confessional_skills`,
  `language_poetry_skills`, `spoken_word_skills`, `instapoetry_skills`), re-keyed to the
  poem's own subject and language.

### Concrete craft anchors (still grounded in the poem)

Alongside the sliders, record these concrete anchors so the write/poet agent has an
image and a turn to begin from — each a plain one-line string, traceable to the poem's
`chapter.json`, never a story beat:

- `image_seed` — one concrete image the poem can open on (a thing, not a theme).
- `volta` — one candidate turn where the poem changes its mind, light, or register.
- `sonic_texture` — the sound the poem leans on (assonance, hard consonants, a refrain,
  a repeated word).
- `line_gesture` — whether the poem runs long/enjambed or breaks short; where the breath
  lands.
- `variety_note` — one or two sentences on how this poem differs from its neighbours.

**Every value is a plain one-line string or a number; nothing reads like plot.** The
record is a tuning of the poem's *voice*, not an outline of events.

## Step 1 — Resolve the Active Filters

Read `filters.json`. A filter is **active** when `autorun` is `true`. Build the active
list in `order` sequence. Treat `workshop` and `override` as always disabled for autorun.

```text
active = [ f for f in filters.json.filters if f.autorun == true ], sorted by f.order
```

For each active filter, note its skill path (e.g. `.framework/filters/workshop/SKILL.md`).
These are the skills you will fuse. If `filters.json` is missing or has no active filters,
stop with a clear error — there is nothing to combine.

## Step 2 — Fuse the Active Skills

Read each active filter's `SKILL.md`. Extract its **task, method, and rules** — not its
identity prose or its output-file boilerplate. Combine them into a single ordered
instruction set, and apply it **poetically**: the research filter becomes image/source
grounding, the correctness filter becomes the check on any factual claim inside a line,
the theme filter becomes the poem's philosophical lens, the syntax filter becomes the
cadence/line-break guidance, and the quality filter becomes the poetic bar (image, music,
turn, resonance).

- **Order matters.** The combined pass applies the filters in `order` sequence, each feeding the next.
- **One pass.** The combined pass reads the poem's `chapter.json` once, applies every active filter's guidance in sequence, and writes the result once.
- **No per-filter files.** The combined pass does not write `content-input.md`, `content-output.md`, or per-filter summaries. It writes only the enrichment record in `chapter.json` and never reads or writes `chapter.md`; workshop alone may create that draft when it is absent, and writing agents own later revisions.

The combined pass's contract is:

1. Read `chapter.json` (never `chapter.md` — it is an output file, not a source).
2. Apply each active filter's guidance in `order` sequence to the poem's metadata and the filters' own outputs.
3. Record the fused enrichment guidance — and the poetic attributes above — in `chapter.json`.
4. Write nothing to `chapter.md`; the writing/authorship path owns that file.
5. Update `chapter.json` with the enrichment result (see Output).

## Step 3 — Execute the Combined Pass

Run the fused instruction set over each target poem. The end product is a single enriched
`chapter.json`, recording that the poem has passed through the fused filter guidance in
`order` sequence. The prose authoring is deferred to the write/poet agents, which read
this enrichment metadata and compose `chapter.md` accordingly.

- **Metadata-only** — the combined pass reads and writes `chapter.json`; it never reads or writes `chapter.md`.
- **Grounded** — every recorded image, motif, and claim is traceable to the poem's own `chapter.json` sources.
- **Form-correct** — the recorded enrichment states the target form `poetry` and names the chosen signature and style.
- **Ready** — no further filter pass is required before write or publish.

## Output

1. **Chapter model** — update `workspaces/pipeline/<bookname>/chapters/<n>/chapter.json` without dropping unrelated fields:
   - `state` — set to `"enriched"`.
   - `enrich` — an object recording the result: `{ active_filters: [...], status: "enriched" }`, where `active_filters` lists the fused filter names in order.
   - `stereotype` — the poetic signature: `{ signature: "<poet>", style: "<desh|pijush|...>" }`.
   - `creative_enrichment.poetic_parameters` — the style-slider profile: the five
     numeric sliders (`emotional_rawness`, `grammatical_abstraction`, `structural_rigidity`,
     `rhythmic_urgency`, `digital_simplicity`), the `movement` (name + one-liner), the
     `writing_skills`, and the concrete anchors (`image_seed`, `volta`, `sonic_texture`,
     `line_gesture`, `variety_note`), merged into any existing `creative_enrichment`
     without discarding it.

`chapter.md` is **not** written here; it is written only later by the writing/authorship
agents. Do not write to `workspaces/published/`. Do not create per-filter files. Do not overwrite
unrelated `chapter.json` fields.

## Report

Report the resolved active filters, the fused order, the poetic signature and style
assigned, the poems processed, and the resulting `state`.
