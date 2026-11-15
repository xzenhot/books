# Poetry Craft Registry (History Corpus)

A catalog of the **poetry craft taxonomy corpus** in `.framework/editor/history/` — the
historical, formal, and evaluative knowledge base for poetry composition.

> **Status: ORPHANED — not yet wired into the framework.**
> No agent, workflow, rule, filter, or tool currently reads this directory.
> This registry records what exists, what it is for, and how it should be integrated.

---

## Available Sources

| # | File | Domain | Entries | Lines | Bytes | Status |
|---|------|--------|--------:|------:|------:|--------|
| 1 | `classification.md` | Poetic classifications (macro-genre) | 16 top-level + sub-classifications | 107 | 11,793 | Orphaned |
| 2 | `Era.md` | Historical eras | 12 | 121 | 13,510 | Orphaned |
| 3 | `geo.md` | Linguistic-geographical spheres | 11 | 107 | 11,651 | Orphaned |
| 4 | `movement.md` | Movements & schools | 34 | 157 | 14,675 | Orphaned |
| 5 | `quality.md` | Quality metrics | 20 | 66 | 7,208 | Orphaned |
| 6 | `types.md` | 16-dimension metadata schema | 16 | 89 | 8,865 | Orphaned |

**Total corpus:** 6 files, 647 lines, 67,702 bytes.

---

## What Each Source Contains

### 1. `classification.md` — 16 Poetic Classifications

The macro-genre taxonomy of poetry itself. Each entry carries sub-classifications with
historical exemplars.

| # | Classification | Example Sub-classifications |
|---|---|---|
| 1 | Narrative & Epic | Primary/oral epic, literary epic, verse novel, ballad |
| 2 | Pure Lyric | Monodic/melic, Pindaric ode, Horatian ode, East Asian shi/ci |
| 3 | Dramatic | Verse tragedy/comedy, Eastern verse theater, dramatic monologue, closet drama |
| 4 | Elegiac & Memorial | Pastoral elegy, dirge/epitaph, elegiac couplet, modern anti-elegy |
| 5 | Devotional, Mystical & Sacred | Liturgical/hymnic, Sufi masnavi, Bhakti song, metaphysical devotion |
| 6 | Pastoral & Bucolic | Idyll/eclogue, georgic, anti-pastoral, urban pastoral |
| 7 | Didactic & Philosophical | Cosmological treatise, gnomic verse, epistolary/critical verse |
| 8 | Satirical & Epigrammatic | Formal verse satire, epigram, burlesque/parody/doggerel |
| 9 | Erotic, Courtly & Amatory | Courtly love, canzoniere, classical erotic, carpe diem |
| 10 | Architectural & Fixed-Form | Sonnet family, refrain/cycling forms, ghazal/rubaiyat |
| 11 | Minimalist & Syllabic | Japanese micro-forms, syllabic verse, aphoristic fragments |
| 12 | Free Verse & Organic Cadential | Biblical/Whitmanian long line, imagist, projective/open field |
| 13 | Avant-Garde, Concrete & Conceptual | Visual/pattern, concrete, sound poetry, erasure/found |
| 14 | Political, Protest & Witness | War poetry, poetry of witness, post-colonial/Negritude, agitprop |
| 15 | Confessional & Psycho-Lyric | First-generation confessional, deep image/oneiric, somatic/trauma |
| 16 | Oral, Performative & Folk | Griot/praise, slam/spoken word, work songs/spirituals, choral chant |

**Use:** the correct replacement for `.framework/editor/poetry/genre/`, which currently
holds a byte-identical copy of the *novel* genre corpus (see Defect D3).

### 2. `Era.md` — 12 Historical Eras

Chronological placement with global hubs, poetic impulse, and key figures per era.

| # | Era | Span |
|---|---|---|
| 1 | Dawn of Inscription & Bronze Age Antiquity | c. 3000 - 8th c. BCE |
| 2 | Classical & Axial Age | c. 8th c. BCE - 5th c. CE |
| 3 | Early Middle Ages & Post-Classical Golden Ages | c. 5th - 10th c. CE |
| 4 | High & Late Middle Ages | c. 10th - 14th c. |
| 5 | Early Modern: Renaissance & Baroque | c. 15th - late 17th c. |
| 6 | Long Eighteenth Century: Enlightenment & Neoclassicism | c. 1680s - 1780s |
| 7 | Nineteenth I: Romanticism & Transcendentalism | c. 1780s - 1840s |
| 8 | Nineteenth II: Victorian, Parnassian, Symbolist | c. 1840s - 1900 |
| 9 | Early 20th: Avant-Garde & High Modernism | c. 1900 - 1945 |
| 10 | Mid-20th: Post-War, Cold War, Decolonization | c. 1945 - 1970s |
| 11 | Late 20th: Postmodernity, Polyphony, Theory | c. 1970s - 1990s |
| 12 | 21st Century: Digital, Transnational, Anthropocene | 2000s - present |

**Use:** the answer to the `history` filter's *"Era markers"* requirement, which today
has no corpus to check against.

### 3. `geo.md` — 11 Linguistic-Geographical Spheres

How a language's phonetic engine and a region's landscape shape its prosody.

| # | Sphere | Prosodic DNA |
|---|---|---|
| 1 | Sinitic & East Asian | Tonal balancing (ping/ze), 5/7-character lines, visual parallelism |
| 2 | Japanese Archipelago | Moraic syllable counts (5-7-5), yugen, mono no aware |
| 3 | Indic & South Asian | Quantitative chandas (laghu/guru), rasa, dhvani, matra counting |
| 4 | Semitic (Arabic/Hebrew/Ethiopic) | Al-Arud 16 meters, triconsonantal rhyme, semantic parallelism |
| 5 | Iranic & Central Asian | Aruz meters, radif/qafiya refrain, dual secular-Sufic register |
| 6 | Greco-Roman & Mediterranean | Quantitative long/short syllables, hyperbaton, genre decorum |
| 7 | Romance Sphere | Syllabic counting, vowel-dense intricate rhyme, sonnet/canzone |
| 8 | Germanic & Global Anglophone | Stress-timed alliterative -> accentual-syllabic iambic |
| 9 | Slavic & Eastern European | Inflected case, free word order, syllabo-tonic, dense feminine rhyme |
| 10 | Sub-Saharan African | Tonal languages, percussive polyrhythm, praise names, call-and-response |
| 11 | Indigenous Americas & Oceanic | Semantic couplets (difrasismo), cyclic ceremonial chant |

**Use:** the source for the `spatality` filter's prosody decisions. **Bengali sits in
Sphere 3** — relevant to every book in this workspace.

### 4. `movement.md` — 34 Movements & Schools

Nine chronological epochs of collective poetic alignment.

| Epoch | Movements |
|---|---|
| I. Classical & Traditional (Antiquity-14th c.) | 1 Greco-Roman Poetics, 2 Sanskrit Kavya, 3 Tang & Song, 4 Persian Sabk |
| II. Medieval & Early Vernacular (11th-15th c.) | 5 Troubadour/Fin'amor, 6 Dolce Stil Novo, 7 Bhakti & Sufi |
| III. Renaissance, Baroque, Metaphysical (16th-17th c.) | 8 La Pleiade, 9 Metaphysical Poets, 10 Baroque/Conceptist |
| IV. Neoclassicism vs Romanticism (18th-19th c.) | 11 Neoclassical/Augustan, 12 Romantic Movement |
| V. Late 19th Reactions (1850-1900) | 13 Parnassianism, 14 French Symbolism, 15 Aesthetic/Decadent, 16 Modernismo |
| VI. Early 20th Avant-Gardes (1900-1930s) | 17 Imagism, 18 Futurism, 19 Acmeism, 20 Expressionism, 21 Dada/Surrealism |
| VII. High Modernism & Mid-Century (1920s-1950s) | 22 High Modernism, 23 Harlem Renaissance, 24 Negritude |
| VIII. Post-WWII (1950s-1980s) | 25 Confessional, 26 Beat, 27 Black Mountain, 28 New York School, 29 Black Arts, 30 Language Poetry |
| IX. Contemporary (1980s-present) | 31 New Formalism, 32 Conceptual Poetry, 33 Ecopoetics, 34 Spoken Word/Slam |

**Use:** the discovery layer for `poetry-slider.json`, which today names only **7** of
these 34 (see Defect D4).

### 5. `quality.md` — 20 Quality Metrics

Five evaluative dimensions, each with a criterion and a concrete test.

| Dimension | Metrics |
|---|---|
| I. Language, Diction & Mechanics | 1 Lexical Inevitability, 2 Syntactic/Lineate Tension, 3 Verbal Compression, 4 Phonaesthetics |
| II. Movement, Rhythm & Architecture | 5 Prosodic/Cadential Mastery, 6 Structural Coherence, 7 The Kinetic Turn (Volta), 8 Eloquence of Omission |
| III. Image, Trope & Perception | 9 Metaphoric Vitality, 10 Defamiliarization, 11 Sensory Immediacy/Objective Correlative |
| IV. Tone, Affect & Intellect | 12 Emotional Authenticity vs Sentimentality, 13 Tonal Nuance/Irony, 14 Polysemy/Dhvani, 15 Philosophical Gravitas |
| V. Voice, Tradition & Durability | 16 Distinctiveness of Idiolect, 17 Intertextual Dialogue, 18 Aesthetic Transport/Rasa, 19 Inevitability of Closure, 20 Durability |

**Use:** the testable rubric the `quality` filter lacks (see Defect D5).

### 6. `types.md` — 16-Dimension Metadata Schema

A proposed metadata model in five macro-categories, then re-listed as a 16-item
implementation blueprint (Parts I-IV).

| Category | Dimensions |
|---|---|
| Structural Metadata (Form & Prosody) | Form Type, Stanzaic Structure, Meter Type, Line Metric Count, Rhyme Scheme |
| Historical & Cultural Metadata | Chronological Era, Date of Composition, Geocultural Origin, Language & Dialect |
| Philosophical & Aesthetic Metadata | Literary Movement, School/Collective |
| Stylistic & Linguistic Metadata | Diction Level, Tone/Mood Profile, Dominant Literary Devices |
| Content & Thematic Metadata | Macro Theme, Subject Tags, Poetic Mode |

**Blueprint expansion (Parts I-IV):** Form & Geometry, Rhymes & Echoes, Metre & Prosody,
White Space & Spatial Typography, Word Selection, Imagery Profiles, Comparative Devices,
Rhetorical Syntax, Signature, Subjects, Theme, Style, Generative Methods, Structural
Execution Methods, Constraint-Driven Methods (Oulipo), Revision & Compression Methods.

**Use:** the schema for `book.json` / `chapter.json` poetic fields and for the
`poetic_parameters` block enrich writes (see Defect D6).

---

## Defects

| ID | Severity | Defect | Fix |
|---|---|---|---|
| **D1** | blocker | **Entire directory is orphaned.** Zero references across `.framework/**` (agents, workflows, rules, skills, filters) and `tools/*.py`. 67 KB of the framework's deepest poetry knowledge is unreachable. | Wire into the poetry filters (see *Integration Plan*). |
| **D2** | major | **No per-form split.** `editor/history/` sits as a sibling of `editor/poetry/` and `editor/novel/`, breaking the `editor/<form>/<corpus>/` convention. Content is effectively poetry-only — a single incidental mention of "novel" in 107 lines. | Move to `editor/poetry/history/`, or declare it explicitly shared and add a form-resolution note. |
| **D3** | major | **`poetry/genre/` is a byte-identical clone of `novel/genre/`** — 19/19 registry files identical. Poetry's actual taxonomy (`classification.md`, 16 poetic classifications) is stranded here instead. | Replace `poetry/genre/` seed sources with the `classification.md` taxonomy. |
| **D4** | major | **`movement.md` (34) vs `poetry-slider.json` (7)** — enrich's operative slider knows Stoicism, Sufism, Confessionalism, Language Poetry, New Formalism, Spoken Word, Instapoetry. Twenty-seven documented movements cannot be selected. | Extend `poetry-slider.json` with `parameter_weights` for the remaining 27, or document the 7 as a deliberate shortlist. |
| **D5** | major | **`quality.md` (20 metrics) vs quality filter (5 dimensions)** — the filter audits `subject -> genre -> theme -> syntax -> signature` with no measurable test. The 20 metrics are the missing rubric. | Make `quality.md` the quality filter's scoring appendix. |
| **D6** | minor | **`types.md` is self-duplicated** — its 5 categories appear twice (headings + Parts I-V), and its 16-dimension schema competes with `.framework/rules/style-signature-quality.md`'s 3-layer model (Style/Signature/Theme) without reconciling. | Deduplicate; state explicitly which dimensions map to Style, Signature, Theme. |
| **D7** | minor | **Naming inconsistency** — `Era.md` (capitalized) among `geo.md`, `movement.md`, `classification.md`, `quality.md`, `types.md` (lowercase). All sibling corpora use lowercase. | Rename to `era.md`. |
| **D8** | minor | **No machine-readable form.** All six files are prose blobs with numbered headings. Nothing is JSON/YAML, so no tool can load a taxonomy. | Add `.json` companions, or restructure as front-matter + tables. |
| **D9** | info | **No audit metadata** — correct, since `.framework/**` is exempt from `updated_by`/`updated_date`. No action. | — |

---

## Integration Plan (how to improve poetry writing)

The corpus answers four questions the poetry pipeline currently cannot answer. Each
maps to an existing filter that is starved of input.

### Priority 1 — `history` filter needs `Era.md` + `geo.md`

Today the history filter instructs *"Era markers - dates, reigns, dynasties"* and
*"Place - geography, cities, routes, architecture"* but names no corpus. It can only
re-derive from the book's own gist, so it cannot tell a poem it is set in the High
Tang or the Anthropocene, or that Bengali prosody is quantitative-moraic (Sphere 3)
rather than stress-timed (Sphere 8) — a distinction that changes every line.

```text
.framework/editor/poetry/filters/history/SKILL.md
  + Inputs: `.framework/editor/history/Era.md`, `.framework/editor/history/geo.md`
  + Method: resolve the book's era -> read its "Poetic Impulse" -> constrain the poem's
            formal options to those available in that era AND that geo-sphere.
```

### Priority 2 — `genre` filter needs `classification.md`

The poetry genre filter currently resolves against `poetry/genre/<genre>/registry.md`,
which are copies of the novel's genre seeds (*Treasure Island*, *The Great Gatsby*).
A poem assigned "adventure" is measured against a prose novel.

```text
.framework/editor/poetry/genre/  <- replace seed sources with classification.md entries
.framework/editor/poetry/filters/genre/SKILL.md
  + Registry: `.framework/editor/history/classification.md` (16 poetic classifications)
```

### Priority 3 — `movement` filter needs the 27 missing movements

The enrich pass records `movement` into `poetic_parameters`, but only 7 are reachable.
Adding the rest gives enrich 34 voices instead of 7 — the single highest-leverage
change for poetic variety across a long book.

```text
.framework/editor/poetry/poetry-slider.json
  + movements[] += the 27 from movement.md, each with era, key_figures,
                   one_liner, parameter_weights (5 sliders)
```

### Priority 4 — `quality` filter needs `quality.md` as its rubric

The quality gate records `{ status, notes }` with no test. The 20 metrics supply exact
tests (*"If a synonym can replace a word without destabilizing the rhythm, the diction
is slack"*) that turn a subjective pass into an auditable one.

```text
.framework/editor/poetry/filters/quality/SKILL.md
  + Rubric: `.framework/editor/history/quality.md` — score each of the 20 metrics,
             record per-metric evidence in `quality_review.notes`
```

### Priority 5 — `types.md` should define the poetic metadata schema

`enrich` writes `poetic_parameters` with 5 numeric sliders plus anchors. `types.md`
proposes 16 orthogonal dimensions. Reconciling them makes `chapter.json` carry a
complete, queryable poetic description.

```text
rules/style-signature-quality.md  <- reconcile the 3-layer model with types.md's 16
chapters/<n>/chapter.json          <- add a `poetics` block keyed by types.md dimensions
```

---

## Conventions

- **This is a discovery layer, not a content layer.** Like `themes/`, `signatures/`, and
  `references/`, these files are read-only inputs. Filters read them; nothing modifies
  them.
- **One file = one axis of classification.** `classification.md` (kind), `Era.md` (when),
  `geo.md` (where/which language), `movement.md` (with whom), `quality.md` (how good),
  `types.md` (how to describe it). Do not merge axes.
- **History is not the same as the `history` filter.** The filter verifies a poem's
  historical claims; this corpus supplies the historical framework the filter reasons
  within.
- **No audit stamp.** `.framework/**` is exempt from `.framework/rules/audit-metadata.md`.
- **Every entry needs a machine-readable home.** Until a `.json` companion exists, an
  agent must parse prose — acceptable for an LLM, unusable for `tools/`.

---

## Cross-References

| Related | Relationship |
|---|---|
| `.framework/editor/poetry/genre/` | Should source its classifications from `classification.md` (Defect D3) |
| `.framework/editor/poetry/poetry-slider.json` | Should source its movements from `movement.md` (Defect D4) |
| `.framework/editor/poetry/filters/{history,genre,movement,quality}/SKILL.md` | The consumers this corpus should feed (Defect D1) |
| `.framework/rules/style-signature-quality.md` | Competes with `types.md`'s schema; needs reconciliation (Defect D6) |
| `.framework/editor/subjects/` | Subjects = *what* is written about; this corpus = *how* poetry is classified |
| `.framework/editor/poetry/references/` | Reference works = source texts; this corpus = taxonomy over them |