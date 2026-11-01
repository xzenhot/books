# Override — poetry pipeline (chand)

- **updated_by:** write
- **updated_date:** 2026-11-01T18:25:41Z

## Identity

The **poetry pipeline** override. It applies to every **poem** in this book.

This command file is the human-in-the-loop layer, layered **after** the book's master
prompt at `workspaces/pipeline/chand/override.md`. The master prompt governs identity,
premise, form, language, and craft; this file adds optional per-poem refinements.

## Model Updates

Record the resulting mandate in each poem's model under `chapters/<n>/chapter.json`:

- `override.status` — `"applied"` when a mandate is present, `"passed_through"` when not.
- `override.applied` — the recorded mandates, exactly as written.

`chapter.md` is never read or written here; the writing path owns that file.

## Instruction Scope

Every poem: chapter 1 through chapter 6 of `book.json`'s `chapters[]` array.

---

## Instructions
