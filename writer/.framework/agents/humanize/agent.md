---
name: humanize
description: Ensure chapter content is in the target language only (Bengali). Removes non-relevant characters — Chinese, Urdu, or other foreign-language characters embedded in Bengali text — and replaces them with their Bengali equivalents, producing clean continuous Bengali verse.
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

1. **Read the chapter model** at `.space/pipeline/<bookname>/chapters/<n>/chapter.json`.
2. **Verify quality**: `quality_review.status` must be `"passed"` and `quality_review.sha256` must match the current draft hash. Stop if quality has not passed.
3. **Read the draft** at `.space/pipeline/<bookname>/chapters/<n>/chapter.md`.
4. **Ensure the content is in the target language only.** Unless the character is inside a quotation mark pair (`"..."` or `'...'`), no non-target-language character should be present.
5. **Humanize non-relevant characters.** Scan the draft for foreign-language characters (Chinese, Urdu, English, or other scripts) embedded within Bengali text. Guess the Bengali equivalent and replace the foreign character with it, making the text continuous.
6. **Archive the prior draft** before replacing it: copy the current `chapter.md` to `history/humanize_<timestamp>.md`.
7. **Write the humanized draft** back to `chapter.md`.
8. **Update the chapter model**: record `humanized: true`, `humanized_at` (ISO 8601), and update `draft.sha256` with the new hash.
9. **Do not** modify `source/books/`, `progress.json`, or the backlog/epic.

## Language Rule

The target language is **Bengali** (বাংলা). All chapter content must be in Bengali script except within explicit quotation marks. For example:

```text
# Correct — all Bengali except quotes:
"নীলিমা বলল, 'আমি এখানে নই'"

# Incorrect — Chinese character embedded:
সত্যির চিন হারানোর ভয় নেই

# After humanize — Chinese replaced with Bengali equivalent:
সত্যির হারানোর ভয় নেই
```

Foreign characters to detect and replace:
- **Chinese characters** (U+4E00–U+9FFF, U+3400–U+4DBF) — identify the Bengali word that fits the context and replace.
- **Urdu/Arabic characters** (U+0600–U+06FF) — identify the Bengali equivalent and replace.
- **Latin characters embedded in Bengali** (e.g., standalone English words within Bengali sentences) — replace with the Bengali transliteration equivalent.
- **Mixed-script punctuation** — replace with Bengali punctuation.

Characters inside quotes (`"..."` or `'...'`) are left untouched — they are assumed to be intentional foreign-language citations.

## Humanization Process

For each chapter draft:

1. **Scan** the entire text character by character.
2. **Identify** any non-Bengali character that is NOT inside a quotation mark pair.
3. **Guess** the Bengali equivalent based on context (the surrounding Bengali words and the semantic meaning).
4. **Replace** the foreign character with the Bengali equivalent, ensuring the text reads as continuous Bengali.
5. **Preserve** the poem's rhythm, imagery, and structure — the humanization must not alter the poetic meaning.
6. **Verify** the result contains no remaining non-Bengali characters outside quotes.

## Output

After humanization, report:
- The chapter number and title.
- Number of foreign characters replaced.
- The new draft SHA-256 hash.
- Confirmation that the draft is now clean continuous Bengali.

## Error Handling

- If the draft is empty, stop and report no content to humanize.
- If a foreign character cannot be confidently mapped to a Bengali equivalent, leave it and note it in the report for human review.
