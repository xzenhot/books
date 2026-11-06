# Syntax Registry (Poetry)

A catalog of every syntax sample available in `.framework/context/poetry/syntax/`.
Each syntax sample defines the **sentence-level structure and register** for a chapter —
how the prophetic/elevated register is shaped into current, readable syntax. A syntax
sample supplies the *how the sentence is built*; it never fixes meter/rhyme (that is a
style) and never assigns themes (that is a theme set).

The syntax filter reads this registry to discover available samples, then reads the
chosen `syntax.md` for the full definition.

---

## Available Syntax Samples

| # | Folder | Register | Source | Status |
|---|--------|----------|--------|--------|
| 1 | `generic/` | Prophetic / Stoic (archaic-literary) | Marcus Aurelius — *The Meditations* | ✅ Active |
| 2 | `gosai_bangla/` | Baul-Fakir (মরমি) | Gosai lexicon | ✅ Active |

---

## Conventions

- **One syntax sample = one register.** Each `syntax.md` defines the sentence shape for a
  single tradition's register.
- **Syntax is structure, not content.** It shapes how sentences read; it never assigns
  themes, defines a poet-voice, or carries the creative bar. See
  `.framework/rules/style-signature-quality.md`.
- **Syntax files are read-only inputs.** The syntax filter reads them; it never modifies
  them.
