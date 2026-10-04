# Mandatory Draft Version Before Overwrite

Every write agent, poet agent, and any delegated skill or helper that replaces an
existing `chapter.md` MUST preserve the previous file in a new version folder
**before** opening the live file for writing, truncating it, or replacing it. This
applies to direct agent calls, revisions, retries, `write all`, and `write
continue`, not only the top-level write command.

1. Read the existing draft and retain its original bytes. If `chapter.md` does not
   exist, this is a first write and no prior-version copy is required. An existing
   empty file must still be archived.
2. Resolve the owning segment `<x>`: poetry always uses `1`; novels use the actual
   segment number (`1`, `2`, ...), incrementing as the chapter advances through its
   segments. A revision does not itself advance the segment number. If the owning
   novel segment is ambiguous, require an explicit segment selection.
3. Copy the previous chapter bytes to
   `workspaces/pipeline/<bookname>/chapters/<n>/segments/<x>/version/chapter_v<k>.md`.
   Choose `<k>` as one greater than the highest existing chapter revision, starting
   at `1`, and create the file exclusively; on a collision, choose the next unused
   number. Never overwrite or move existing copies.
4. Read the archived copy back and verify byte-for-byte equality with the previous
   live file. If the copy or verification fails, stop that chapter without
   overwriting the live draft or marking the write complete.
5. Immediately before replacement, verify that the live file still matches the
   bytes archived. If another process or agent changed it, stop and re-read the
   latest file rather than overwriting an unarchived revision. Save the new draft
   through a temporary file and atomic replacement only after the archive is
   verified.
6. Take a new snapshot before every subsequent replacement, including another
   revision within the same invocation. A previously published version, a backup of
   `model.json`, or the newly generated text does not substitute for a copy of the
   actual draft being replaced.
7. Report each overwritten draft's archive path alongside its new output path. A
   successful write requires the prior-version copy whenever a previous draft
   existed.

These are pipeline draft versions, separate from the reader-facing versions under
`source/books/`. They do not promote unfinished text or bypass validation. This
rule explicitly authorizes a `version/` folder under each segment and takes
precedence over less specific archive instructions in writing agents and skills.
