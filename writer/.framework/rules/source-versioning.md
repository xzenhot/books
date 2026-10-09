# Source Versioning

Reader-facing output is always versioned. The workflow must never write finished
chapters directly under `workspaces/published/<bookname>/` or an unversioned
`workspaces/published/<bookname>/chapters/` folder.

For every `/book <bookname> write <n>|range|all|continue <language>` invocation:

1. Resolve the final output root as `workspaces/published/<bookname>/`.
2. Inspect existing numeric child folders under that root.
3. Choose `<version>` as one greater than the highest numeric folder, or `1` if
   none exist.
4. Create `workspaces/published/<bookname>/<version>/chapters/`.
5. Write all chapters selected by this invocation into that version's `chapters/`
   folder.
6. Assemble that version's consolidated book at
   `workspaces/published/<bookname>/<version>/book.md`.
7. Report the version number and version folder.

Existing versions are immutable reader-facing snapshots. Do not overwrite files in
an older version unless the user explicitly names that version and asks for repair.
