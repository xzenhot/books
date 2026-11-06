# Desh Style — Corpus Analysis

A lexical, syntactic, and structural analysis of the ten canonical poems in
`examples.md` (১–১০). This document records the *surface habits* of the corpus —
what words recur, how sentences are built, how the subject–verb–object order bends,
and how long the units run — so a new poem can reproduce the voice's texture, not
just its imagery.

> **Scope note.** These counts are a close reading of the corpus, not a machine
> tokenizer. Bengali tokenizes on word boundaries (vowel signs are never word
> separators), and the corpus mixes *sadhubhasha* spellings with modern forms and a
> few OCR-style variants (e.g. "কষন্ধ" for "কবন্ধ", "এয়াগত"). Counts below are
> therefore faithful but approximate; they describe *tendency*, which is what a
> writer actually needs.

---

## 1. Word Usage & Frequency

### 1.1 The highest-frequency nouns and their families

The corpus orbits a small, closed vocabulary. The same roots repeat across all ten
poems; this repetition *is* the method (see §6 of `signature.md`).

| Word / root | Rough recurrence | Family |
|---|---|---|
| মড়া / শব (corpse) | highest — appears in nearly every poem | Corpse & cremation |
| শ্মশান (cremation ground) | high | Corpse & cremation |
| শকুন (vulture) | high | Corpse & cremation |
| শৃগাল (jackal) | high | Corpse & cremation |
| কবন্ধ (headless torso) | high | Corpse & cremation |
| সাপ / বিষ / ফনা / ছোবল (snake / poison / hood / strike) | high | Serpent |
| কালী | recurring | Cosmic & mythic |
| আকাশ (sky) | recurring | Cosmic & mythic |
| পেট (belly) | high | Dissolving body |
| গর্ভ (womb) | high | Dissolving body |
| পাঠ / পাঠক / গ্রন্থ / শ্লোক (reading / reader / book / verse) | high | Reading & poetry |
| বোধি / তথাগত / সহস্রার | recurring | Cosmic & mythic |

**Key finding:** the corpus does not reach for a wide dictionary. It *re-keys a narrow
set of roots into many grammatical forms* (মড়া → শবসাধনা → শবদেহ; সাপ → ফনা →
বিষদাঁত). This is a closed, incantatory vocabulary, not an expansive one.

### 1.2 Function-word rhythm

- **"এসব…" (these…)** and **"এক ভ্রমণে…" (on one journey…)** are the two dominant
  anaphoric engines (poems ৩ and ৪).
- **Rhetorical "কার…?" (whose…?)** and **"কী…?" (what…?)** open many questions that
  are never answered.

### 1.3 Rare/loaded (*tatsama*) density

The corpus is unusually dense in Sanskritic abstract nouns. A rough per-poem estimate
is **30–50% *tatsama*** in the elevated passages (বীভৎস, অনঙ্গ, ভবগর্ভ, জরা, তামসিক,
সত্ত্বগুণী, ক্ষণচিহ্ণমালাপরিহিতা, প্রপঞ্চ, প্রমাদ, চিদাকাশ, সহস্রার, দণ্ডপ্রাপক). This
density is deliberate — it is the "high register" that the crude/bodily words then
collide against.

---

## 2. Sequences & Distance (N-gram / juxtaposition habits)

### 2.1 The dominant two-term collision pattern

The signature move is a **two-term juxtaposition where a high/abstract term sits
against a low/bodily term in the same breath**:

| Collision | Poem |
|---|---|
| "ওয়াক্ গর্ভের বমি" (vomit of the womb) | ৫ |
| "মুহূর্তের যোনিপদ্মে লীলাশিশ্ন প্রবেশে" | ১ |
| "চিদাকাশে আজ দুপুরের ডাল-ভাত" (everyday inside the cosmic) | — |
| "আকাশ কালীর পোশাক" (sky as Kali's costume) | ১ |

**Distance finding:** the two colliding terms are usually **immediately adjacent or
within one clause** — the shock depends on *zero bridging*. There is no "and", no
"suddenly", no transitional connective. The leap is bare.

### 2.2 The anaphoric chain (repetition as structure)

- Poem ৩ is built almost entirely on **"এসব… এসব… এসব…"** — a list that accumulates
  and then breaks into "এসবে আমিই শুয়ে, স্বধর্ষিত, জটিল শকুন।"
- Poem ৪ builds on **"এক ভ্রমণে…"** repeated, then reverses into "এক ভ্রমণে কাল কাটে
  না। দুই ভ্রমণে জরা।"

**Distance finding:** the repeated head sits at the *start of successive clauses*; the
gap between repetitions is short (one to two clauses), so the litany reads as a
single accumulating breath rather than scattered ornament.

### 2.3 The circular return (long-range repetition)

Poem ১০ opens "কেউ প্রশ্নাতীত ভালো আছে জেনে একা লাগে আজ" and closes "একা লাগে,
প্রশ্নাতীত একা লাগে আজ।" The same phrase recurs at **maximal distance** (first and
last line), so the whole poem is framed by a single repeated image.

---

## 3. Parts of Speech (Heuristic)

The corpus leans hard on three parts of speech, and starves a fourth:

### 3.1 Nouns and nominalizations dominate

- **Verb-turned-nouns and adjective-turned-nouns are frequent** — the corpus prefers
  the *state* over the *act*: "শবসাধনা" (corpse-practice), "পাঠাভ্যাস" (reading-practice),
  "জরা" (decay), "প্রপঞ্চ" (phenomenal illusion). This matches the `signature.md`
  checklist ("verb-turned-nouns and adjective-turned-nouns").

### 3.2 Verbs are short, present, and often dropped

- Finite verbs tend to be **short and in the present habitual**: "খায়", "ওড়ে",
  "থাকে", "জ্বলে", "গড়ায়".
- In the most incantatory lines the verb is **elided** entirely, leaving bare noun
  phrases: "এই তো আমি। দণ্ডপ্রাপক।" (no verb), "কালের পোশাক শূন্য।"

### 3.3 Adjectives cluster before the noun

- Heavy pre-nominal modification is common: "বীর ভূর্জপত্র", "লোলুপ অশিব
  শিক্ষচরিতামৃতের", "গাঢ় সম্ভবনপটীয়সী". The adjective pile-up is a density device.

### 3.4 Pronouns: a fixed first-person "আমি"

- "আমি" (I) is the constant grammatical subject; "তুমি/তোমার" (you) is the unstable
  addressee; "কার" (whose) is the recurring interrogative. There is almost no
  third-person narrative distance — everything is first-person or second-person address.

---

## 4. Subject–Verb–Object Order

Bengali is canonically **SOV** (subject–object–verb). The corpus mostly honors that
base order, but bends it in two signature ways:

### 4.1 Base SOV holds

- "শৃগালেরই মুখে [O] মাথা [O] রাখে [V]" — object(s) precede the verb.
- "নিজের মড়া [O] উল্টো ক'রে [V] শবসাধনার হোতা।" — object before the verb.

### 4.2 Verb-final dropped → noun-final fragments

Because verbs are frequently elided, many "sentences" are actually **object-final or
noun-final fragments** with no verb at all:

- "এই তো আমি। ভোঁতা।" — subject, then bare noun complement.
- "কালের পোশাক শূন্য।" — subject + bare adjective complement, no copula.

**Order finding:** the corpus's most characteristic "sentence" is not SOV but
**S + complement (no verb)** — a noun or adjective that closes the line without any
predicate. This is the syntactic engine of the self-accusation and the open ending.

### 4.3 Fronting for shock

When a verb does lead, the corpus occasionally **fronts the object or the locative**
for emphasis:

- "মুহূর্তের যোনিপদ্মে লীলাশিশ্ন প্রবেশে…" — locative-led.
- "সমস্ত না-থাকা থেকে হেঁটে গিয়ে স্থিতিতে দেখেছি—" — ablative-led, verb deferred.

---

## 5. Sentence Length & Rhythm

### 5.1 The two-sentence economy

The corpus alternates between **two sentence types**:

1. **Long, winding, enjambed sentences** (poems ১, ২, ৪, ৬) — often **15–30+ words**,
   clauses piled and turning on themselves, the full stop delayed.
2. **Short, flat fragments** (poems ৩, ৫, ৭, ১০) — often **2–6 words**, sometimes a
   single word: "একা।", "এই তো আমি।", "ভোঁতা।"

**Length finding:** the rhythm is not a uniform line; it is a **long breath followed
by a short snap**. The long sentence builds; the short sentence lands the shock. Poem
১ ends on a one-word line ("একা।"); poem ৪ lands "এই তো আমি। দণ্ডপ্রাপক। এই তো আমি।
ভোঁতা।"

### 5.2 Approximate per-poem sentence-length profile

| Poem | Dominant sentence shape | Typical words/sentence |
|---|---|---|
| ১ | long incantatory, one-word close | 12–25, ending 1 |
| ২ | long, clause-piled | 12–25 |
| ৩ | anaphoric list, then short close | 8–20, ending 4–6 |
| ৪ | long question + short self-accusation | 8–20, with 3–4 fragments |
| ৫ | short, staccato, fragmentary | 4–12 |
| ৬ | long, breath-heavy | 12–25 |
| ৭ | mixed, line-broken, short | 4–12 |
| ৮ | long, enjambed, erotic | 12–20 |
| ৯ | long, dense, then short close | 10–20 |
| ১০ | line-broken, short-to-medium | 5–12 |

### 5.3 Punctuation as rhythm

- The **dash (–)** and the **question mark (?)**, and the **exclamation (!)** carry
  the voice more than the full stop. Questions do not seek answers; exclamations are
  not exclamations of joy but of indictment.
- The full stop is used to *cut*, not to conclude — it snaps the long sentence into a
  fragment.

---

## 6. Summary of Findings (the reproducible texture)

1. **Vocabulary** is closed and narrow; a handful of roots (corpse, serpent, cosmic,
   belly, reading) recur in many grammatical forms. *Tatsama* density is very high in
   elevated passages.
2. **Collision** is the core device: a high/abstract term and a low/bodily term sit
   adjacent or one clause apart, with **no connective bridge**.
3. **Anaphora** ("এসব…", "এক ভ্রমণে…") and **circular return** provide long-range
   structure; repetition is the engine.
4. **Parts of speech** skew to nouns and nominalizations; verbs are short, present, and
   often dropped; adjectives pile before the noun; "আমি" is the constant subject.
5. **Word order** is base SOV, but the signature "sentence" is **subject + complement
   with no verb** — a noun- or adjective-final fragment.
6. **Sentence length** alternates long (15–30 words) and short (2–6 words), a long
   breath followed by a snap; poems often close on a single word or a short flat clause.
7. **Punctuation** (dash, question, exclamation) carries rhythm; the full stop cuts
   rather than concludes.
