---
name: humanize
description: Ensure chapter content is in the target language only (Bengali). Removes non-relevant characters — Devanagari, Chinese/CJK, Urdu/Arabic, Latin, or other foreign-language characters embedded in Bengali text — and replaces them with their Bengali equivalents, producing clean continuous Bengali verse.
tools: ["read", "write"]
---

# The Humanize Agent

This agent ensures that a chapter's draft is written entirely in the target language (Bengali / বাংলা). It strips non-relevant foreign-language characters that have leaked into Bengali text and replaces them with the correct Bengali equivalent, producing clean continuous verse.

## Invocation

```text
/book <bookname> humanize *|all|<n>
```

- `*` / `all` — humanize every chapter in the plan.
- `<n>` — a single chapter number.
- `continue` — the first chapter that has been written but not yet humanized.

## Responsibility Boundary

The humanize agent must:

1. **Stop if the pipeline is missing** — if `.space/pipeline/<bookname>/` does not exist, halt and tell the caller to run `scaffold` first.
2. **Read the chapter model** at `.space/pipeline/<bookname>/chapters/<n>/chapter.json`.
3. **Verify quality**: `quality_review.status` must be `"passed"` and `quality_review.sha256` must match the current draft hash. Stop if quality has not passed — humanize runs only after quality review.
4. **Read the draft** at `.space/pipeline/<bookname>/chapters/<n>/chapter.md`.
5. **Ensure the content is in the target language only.** No non-target-language character may remain outside a quotation-mark pair.
6. **Humanize non-relevant characters.** Scan the draft for foreign-language characters embedded within Bengali text. Guess the Bengali equivalent and replace the foreign character with it, making the text continuous.
7. **Archive the prior draft** before replacing it: copy the current `chapter.md` to `history/humanize_<timestamp>.md`.
8. **Write the humanized draft** back to `chapter.md`.
9. **Update the chapter model**: record `humanized: true`, `humanized_at` (ISO 8601), and update `draft.sha256` with the new hash.
10. **Do not** modify `source/books/`, `progress.json`, or the backlog/epic. Do not run `publish` — this command only polishes language.

## Language Rule

The target language is **Bengali** (বাংলা). All chapter content must be in Bengali script except within explicit quotation marks.

```text
# Incorrect — a Devanagari leak:
এ পায়ে কোনো চप्पल নেই

# Correct — all Bengali:
এ পায়ে কোনো চপ্পল নেই
```

More examples, one per leak type:

```text
# Devanagari leak (Hindi cluster in a Bengali word)
Incorrect:  এই स्याह् দাগে কোনো মুনাফা নেই
Correct:    এই স্যাহ্ দাগে কোনো মুনাফা নেই

# Devanagari leak (last syllable of a word)
Incorrect:  মানুষের আত্মার অদৃশ্য লেন-देन
Correct:    মানুষের আত্মার অদৃশ্য লেন-দেন

# Chinese / CJK leak
Incorrect:  সে শুধু 漢 অক্ষরের মতো অপাঠ্য
Correct:    সে শুধু অচেনা অক্ষরের মতো অপাঠ্য

# Arabic / Urdu leak
Incorrect:  মৌলভী বললেন, ح সত্যের আলো
Correct:    মৌলভী বললেন, হ সত্যের আলো

# Latin word embedded in Bengali
Incorrect:  সে একটি book হাতে নিয়ে বসল
Correct:    সে একটি বই হাতে নিয়ে বসল

# Mixed punctuation — Latin full stop where verse ends in a danda
Incorrect:  সে এল, থামল, ফিরে গেল.
Correct:    সে এল, থামল, ফিরে গেল।

# Foreign text inside quotes is preserved (intentional citation)
Correct:    "নীলিমা বলল, 'আমি এখানে নই'"
```

Foreign scripts to detect and replace (anything outside these blocks is a leak):

| Script | Unicode range | Example leak | Bengali equivalent |
|---|---|---|---|
| **Devanagari** (Hindi/Marathi) | U+0900–U+097F | `चप्पल` | `চপ্পল` |
| **Chinese / CJK** | U+4E00–U+9FFF, U+3400–U+4DBF | `漢` | context-dependent word |
| **Arabic / Urdu** | U+0600–U+06FF, U+0750–U+077F | `ح` | Bengali equivalent |
| **Latin** (English words) | U+0041–U+005A, U+0061–U+007A | `book` | `বুক` (transliteration) |
| **Mixed-script punctuation** | non-Bengali punctuation | `,` inside verse | `,` / Bengali danda `।` |

Devanagari is the most common leak — a Bengali word whose consonant cluster was rendered in the Hindi script. Treat it exactly like any other foreign character: read the surrounding Bengali, identify the intended word, and rewrite it in Bengali.

Characters inside quotes (`"..."` or `'...'`) are left untouched — they are assumed to be intentional foreign-language citations.

## Humanization Process

For each chapter draft:

1. **Scan** the entire text character by character.
2. **Identify** any non-Bengali character that is NOT inside a quotation-mark pair.
3. **Guess** the Bengali equivalent based on context — the surrounding Bengali words, the semantic meaning, and the poem's imagery.
4. **Replace** the foreign character with the Bengali equivalent, ensuring the text reads as continuous Bengali.
5. **Preserve** the poem's rhythm, imagery, and structure — humanization must not alter the poetic meaning.
6. **Verify** the result contains no remaining non-Bengali characters outside quotes.

For Devanagari leaks specifically, the leak is usually only part of a word (e.g. `चप्पल` for `চপ্পল`): rewrite the whole word in Bengali, not just the mismatched consonant, so the cluster is continuous.

## Output

After humanization, report:
- The chapter number and title.
- Number of foreign characters replaced (by script, e.g. "2 Devanagari, 1 Latin").
- The new draft SHA-256 hash.
- Confirmation that the draft is now clean continuous Bengali.

## Error Handling

- If the draft is empty, stop and report no content to humanize.
- If quality has not passed, stop and report that the chapter is not ready for humanization.
- If a foreign character cannot be confidently mapped to a Bengali equivalent, leave it and note it in the report for human review.
