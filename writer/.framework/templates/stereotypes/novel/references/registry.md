# Reference Registry

A catalog of every reference text available in `stereotypes/novel/references/`. Each reference is a source text — the raw material the writer agent reads for direct stylistic and thematic grounding.

The writer agent reads this registry to discover available references, then reads the individual reference file for the source text itself.

---

## Available References

| # | Reference File | Work | Author | Format | Language | Status |
|---|---------------|------|--------|--------|----------|--------|
| 1 | [`aurilus.txt`](aurilus.txt) | *The Meditations* | Marcus Aurelius | Plain text (full text) | English | ✅ Active |
| 2 | [`gosai_dictionary.txt`](gosai_dictionary.txt) | Gosai/Baul/Fakir spiritual lexicon — "Prose of Leaving Home" | Bengali folk-mystical tradition | Plain text (annotated lexicon) | English | ✅ Active |
| 3 | [`languages_sample.txt`](languages_sample.txt) | "The Right of the Flower" — a philosophical prose sample on rights and nature | Framework sample | Plain text (prophetic-register sample) | English | ✅ Active |

---

## Reference Details

### 1. `aurilus.txt` — The Meditations of Marcus Aurelius

- **Work:** *The Meditations of Marcus Aurelius*
- **Author:** Marcus Aurelius (121–180 CE), Roman Emperor and Stoic philosopher
- **Translation:** Jeremy Collier, revised by Alice Zimmern (1887)
- **Format:** Plain text (`.txt`), full text of the work
- **Language:** English
- **Structure:** 12 Books of aphorisms, reflections, and moral teachings

**Associated Quality:** [`../qualities/aurilus.md`](../qualities/aurilus.md) — the seed analysis of this work.

**Associated Themes:** [`../themes/generic.md`](../themes/generic.md) — the ten Stoic themes derived from this work.

### 2. `gosai_dictionary.txt` — Gosai: Prose of Leaving Home

- **Content:** An annotated spiritual lexicon of the Gosai, Baul, and Fakir traditions of Bengal — the seeker, the wanderer, the person of the heart.
- **Sections:** What Is Home, Who Is a Baul, Who Is a Fakir.
- **Format:** Plain text (`.txt`), annotated dictionary/prose.
- **Language:** English.

**Associated Themes:** [`../themes/gosai_bangla.md`](../themes/gosai_bangla.md) — the ten Baul-Fakir themes derived from this lexicon.

**Associated Syntax:** [`../syntax/gosai_bangla.md`](../syntax/gosai_bangla.md).

### 3. `languages_sample.txt` — The Right of the Flower

- **Content:** A framework-authored philosophical prose sample ("The Right of the Flower") on rights, nature, and mutual belonging, written in the prophetic/literary register.
- **Format:** Plain text (`.txt`), single literary sample.
- **Language:** English.
- **Use:** A style-grounded sample for calibrating the target register across languages.

---

## How to Add a New Reference

1. Add the source text file to `stereotypes/novel/references/`.
2. Add a row to the table above and a detail section below.
3. Create a matching quality file in `stereotypes/novel/qualities/` (the seed analysis of the reference).
4. Create a matching theme set in `stereotypes/novel/themes/` if the reference introduces new themes.
5. Sync the master index at `../registry.md`.

---

## Conventions

- **One reference = one source text.** Each file holds a single work.
- **Reference files are read-only inputs.** The writer agent reads them; it never modifies them.
- **References are distinct from qualities.** A reference is the raw source text; a quality is the *analysis* of that text (voice, metaphor families, quality metrics).
- **References are distinct from themes.** A theme set is the *philosophical lens* derived from the reference.
