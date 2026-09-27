
What I want:

# What this system should do (in plain English)

## Part 1 — Planning a book (`.space/backlog/`)

This is the *idea* stage. Nothing is written yet — you are only deciding what the book will be.

1. Start a new book by giving it a **name** (this creates the book's folder).
2. Every book automatically gets a one-line **gist** (the seed idea) plus a short **summary**.
3. You can change two things at any time:
   - the **type** — **Novel** (prose) or **Poetry** (verse)
   - the **chapter count** — how many chapters / poems
4. The system watches the files: if you **edit the gist by hand**, it notices.
5. When the gist changes → the system writes a detailed story outline called **`storyline.md`**.
6. When `storyline.md` changes → the system writes a chapter plan called **`book.json`**.
7. `book.json` is the **complete blueprint** of the book, built from `storyline.md` + the chapter count.
8. `book.json` must follow the example schema at **`.framework/templates/book.json`**.
9. Each chapter's `chapter_summary` must carry **enough context** to guide writing it later.
10. Word target per piece:
    - **Poetry** → 200–300 words
    - **Novel** → 4500 words per chapter
11. I can **refresh** the gist or the epic at any time, and the system will **regenerate `book.json`** from the updated material (re-deriving the chapter plan and filter chain from the new content).



## Part 2 — Building the book (`.space/pipeline/`)

This is the *writing* stage. The blueprint from Part 1 becomes the actual book.

1. **scaffold** — turn `book.json` into a working folder: one folder per chapter, plus the filter chain.
2. **filters** — each chapter is refined step by step *before* it is written, one filter at a time:
   - Novel: `workshop → research → seeds → correctness → theme → syntax`
   - Poetry: `workshop → research → correctness → theme → syntax → override → quality`
3. **enrich** — optionally fuse the active filters into one combined pass — the sum of all filters **except `override` and `quality`** — to refine chapters in a single run.
4. **style** — pick the voice each chapter is written in (default: `pijush`); this is recorded in `book.json` so the writer knows which style to use.
5. **write** — the actual chapter/poem text is authored here (one chapter, or all), in the style from `book.json`.
6. **quality** — after writing, the final check runs before a chapter is marked done.
7. **translate** — optionally translate a chapter into another language. 
8. **publish** — copy the finished chapters into the final book at `source/books/<bookname>/`.

