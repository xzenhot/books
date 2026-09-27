#!/usr/bin/env python3
"""
FastAPI service wrapping the reusable publish tool.

Exposes the pipeline-to-source publication workflow as HTTP endpoints.

Run:
    uvicorn publish_api:app --reload

Endpoints:
    GET  /health                       -> service health
    GET  /books/{bookname}/versions    -> list existing versioned folders
    POST /publish/{bookname}           -> publish writer-stage segments
    POST /publish/{bookname}/{language}-> publish translator-stage segments
"""
import datetime
import json
import os
import shutil
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

app = FastAPI(
    title="Novelist Publish Service",
    version="1.0.0",
    description=(
        "Promotes the latest writer-stage (or translator-stage) segments from "
        "the pipeline to a new versioned folder under `source/books/<bookname>/` "
        "and assembles the consolidated `book.md`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


class PublishResult(BaseModel):
    bookname: str
    language: Optional[str] = None
    version: str
    version_dir: str
    published: int
    skipped: int
    skipped_details: list[dict]
    book_file: str
    title: str


# ---------------------------------------------------------------------------
# CRUD models
# ---------------------------------------------------------------------------

class CreateBookRequest(BaseModel):
    book_name: str
    book_long_title: Optional[str] = None
    form: str = "poetry"  # "novel" | "poetry"
    language: Optional[str] = None
    generic: Optional[str] = None
    era: Optional[str] = None
    target_audience: Optional[str] = None
    gist: Optional[str] = None
    book_summary: Optional[str] = None


class EditBookRequest(BaseModel):
    book_long_title: Optional[str] = None
    form: Optional[str] = None
    language: Optional[str] = None
    generic: Optional[str] = None
    era: Optional[str] = None
    target_audience: Optional[str] = None
    gist: Optional[str] = None
    book_summary: Optional[str] = None


class ChapterInput(BaseModel):
    chapter_index: Optional[int | str] = None
    chapter_title: Optional[str] = None
    chapter_summary: Optional[str] = None
    word_target: int = 500


class ChapterEditInput(BaseModel):
    chapter_title: Optional[str] = None
    chapter_summary: Optional[str] = None
    word_target: Optional[int] = None
    content: Optional[str] = None


class ChapterContent(BaseModel):
    bookname: str
    chapter: str
    content: str


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _backlog_dir(bookname: str) -> str:
    return os.path.join(ROOT, ".space", "backlog", "epic", bookname)


def _pipeline_dir(bookname: str) -> str:
    return os.path.join(ROOT, ".space", "pipeline", bookname)


def _src_dir(bookname: str) -> str:
    return os.path.join(ROOT, "source", "books", bookname)


def _chapter_dir(bookname: str, chapter: str | int) -> str:
    return os.path.join(_pipeline_dir(bookname), "chapters", str(chapter))


def _read_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_book_plan(bookname: str) -> dict:
    """Load the book plan from backlog book.json (fallback: pipeline)."""
    for d in (_backlog_dir(bookname), _pipeline_dir(bookname)):
        path = os.path.join(d, "book.json")
        if os.path.exists(path):
            return _read_json(path)
    raise HTTPException(
        status_code=404, detail=f"no book plan for '{bookname}'"
    )


def _save_book_plan(bookname: str, plan: dict) -> None:
    """Persist the plan to both backlog and pipeline book.json."""
    for d in (_backlog_dir(bookname), _pipeline_dir(bookname)):
        if os.path.isdir(d):
            _write_json(os.path.join(d, "book.json"), plan)


def _resolve_chapter_identifier(plan: dict, chapter: str) -> str:
    """Resolve a chapter path segment to the canonical name in book.json."""
    chs = plan.get("chapters", [])
    for c in chs:
        if str(c.get("chapter_index")) == chapter or str(c.get("name")) == chapter:
            return str(c.get("chapter_index"))
    return chapter


def publish(bookname: str, language: Optional[str] = None) -> PublishResult:
    BOOK = bookname
    PIPE = os.path.join(ROOT, ".space", "pipeline", BOOK)
    SRC = os.path.join(ROOT, "source", "books", BOOK)

    if not os.path.isdir(PIPE):
        raise HTTPException(
            status_code=404,
            detail=f"pipeline missing for '{BOOK}'. Run scaffold first.",
        )

    os.makedirs(SRC, exist_ok=True)

    # version allocation
    existing = [
        d
        for d in os.listdir(SRC)
        if d.startswith("version") and os.path.isdir(os.path.join(SRC, d))
    ]
    nums = [
        int(d.replace("version", ""))
        for d in existing
        if d.replace("version", "").isdigit()
    ]
    k = max(nums) + 1 if nums else 1
    ver = f"version{k}"
    ver_dir = os.path.join(SRC, ver)
    chapters_out = os.path.join(ver_dir, "chapters")
    os.makedirs(chapters_out, exist_ok=True)

    # canonical order
    with open(os.path.join(PIPE, "bookseed.txt"), encoding="utf-8") as f:
        topics = [line.strip() for line in f if line.strip()]
    total = len(topics)

    def version_key(fname: str) -> int:
        if fname.startswith("chapter_v") and fname[len("chapter_v"):-3].isdigit():
            return int(fname[len("chapter_v"):-3])
        return 0

    published: list[tuple[int, str]] = []
    skipped: list[tuple[int, str]] = []
    for n in range(1, total + 1):
        if language:
            seg_dir = os.path.join(
                PIPE, "chapters", str(n), "segments", "1", "translator"
            )
            if not os.path.isdir(seg_dir):
                skipped.append((n, f"no translator segment for '{language}'"))
                continue
            candidates = [
                f
                for f in os.listdir(seg_dir)
                if f.lower().startswith(language.lower()) and f.endswith(".md")
            ]
            if not candidates:
                skipped.append((n, f"no translator segment for '{language}'"))
                continue
            src_file = os.path.join(seg_dir, candidates[0])
            out_dir = os.path.join(chapters_out, str(n), language)
        else:
            seg_dir = os.path.join(
                PIPE, "chapters", str(n), "segments", "1", "writer"
            )
            if not os.path.isdir(seg_dir):
                skipped.append((n, "no writer segment"))
                continue
            files = [f for f in os.listdir(seg_dir) if f.endswith(".md")]
            if not files:
                skipped.append((n, "no writer segment"))
                continue
            files.sort(key=version_key)
            src_file = os.path.join(seg_dir, files[-1])
            out_dir = os.path.join(chapters_out, str(n))

        os.makedirs(out_dir, exist_ok=True)
        out_chapter = os.path.join(out_dir, "chapter.md")
        shutil.copyfile(src_file, out_chapter)
        published.append((n, out_chapter))

    # assemble book.md
    title = "Book"
    model_path = os.path.join(PIPE, "book.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(PIPE, "model.json")
    if os.path.exists(model_path):
        with open(model_path, encoding="utf-8") as f:
            model = json.load(f)
        title = model.get("book_long_title", "Book")

    parts = [f"# {title}\n"]
    for _, cp in published:
        with open(cp, encoding="utf-8") as f:
            parts.append(f.read().strip())
        parts.append("\n---\n")
    book_md = "\n\n".join(parts).rstrip() + "\n"

    book_name = f"book_{language}.md" if language else "book.md"
    with open(os.path.join(ver_dir, book_name), "w", encoding="utf-8") as f:
        f.write(book_md)

    # progress update
    pp = os.path.join(PIPE, "progress.json")
    if os.path.exists(pp):
        with open(pp, encoding="utf-8") as f:
            prog = json.load(f)
        prog["published"] = True
        prog["published_at"] = datetime.datetime.now(datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        prog["published_version"] = k
        if language:
            prog["published_language"] = language
        with open(pp, "w", encoding="utf-8") as f:
            json.dump(prog, f, indent=2, ensure_ascii=False)

    return PublishResult(
        bookname=BOOK,
        language=language,
        version=ver,
        version_dir=ver_dir,
        published=len(published),
        skipped=len(skipped),
        skipped_details=[
            {"chapter": n, "reason": r} for n, r in skipped
        ],
        book_file=os.path.join(ver_dir, book_name),
        title=title,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "publish"}


@app.get("/books/{bookname}/versions", response_model=list[str])
def list_versions(bookname: str) -> list[str]:
    SRC = os.path.join(ROOT, "source", "books", bookname)
    if not os.path.isdir(SRC):
        raise HTTPException(
            status_code=404, detail=f"no source folder for '{bookname}'"
        )
    return sorted(
        d
        for d in os.listdir(SRC)
        if d.startswith("version") and os.path.isdir(os.path.join(SRC, d))
    )


@app.post("/publish/{bookname}", response_model=PublishResult)
def publish_writer(bookname: str) -> PublishResult:
    return publish(bookname)


@app.post("/publish/{bookname}/{language}", response_model=PublishResult)
def publish_translator(bookname: str, language: str) -> PublishResult:
    return publish(bookname, language)


# ---------------------------------------------------------------------------
# Book CRUD
# ---------------------------------------------------------------------------

@app.post("/books", status_code=201)
def create_book(req: CreateBookRequest) -> dict:
    """Create a new book: backlog artifacts + pipeline skeleton."""
    bookname = req.book_name
    if not bookname or any(ch in bookname for ch in "\\/ "):
        raise HTTPException(status_code=400, detail="invalid book_name")

    backlog = _backlog_dir(bookname)
    if os.path.exists(os.path.join(backlog, "book.json")):
        raise HTTPException(status_code=409, detail=f"book '{bookname}' already exists")

    form = req.form if req.form in ("novel", "poetry") else "poetry"
    title = req.book_long_title or bookname.title()
    now = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    plan = {
        "book_name": bookname,
        "book_long_title": title,
        "generic": req.generic or "",
        "era": req.era or "",
        "language": req.language or "English",
        "target_audience": req.target_audience or "",
        "chapter_count": 0,
        "form": form,
        "book_summary": req.book_summary or "",
        "created_at": now,
        "user_name": "api",
        "gist": req.gist or "",
        "chapters": [],
        "word_target": 500,
    }
    _write_json(os.path.join(backlog, "book.json"), plan)

    # gist.md / epic.md
    gist_text = req.gist or ""
    with open(os.path.join(backlog, "gist.md"), "w", encoding="utf-8") as f:
        f.write(f"# {title} - Gist\n\n## Gist\n\n{gist_text}\n")
    with open(os.path.join(backlog, "epic.md"), "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{req.book_summary or gist_text}\n")

    # pipeline skeleton
    pipe = _pipeline_dir(bookname)
    os.makedirs(os.path.join(pipe, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(pipe, "filters"), exist_ok=True)
    _write_json(os.path.join(pipe, "book.json"), plan)
    model = {
        "form": form,
        "book_name": bookname,
        "book_long_title": title,
        "language": req.language or "English",
        "chapter_count": 0,
        "source_terms": [],
        "gist": req.gist or "",
        "book_summary": req.book_summary or "",
        "created_at": now,
    }
    _write_json(os.path.join(pipe, "book.json"), model)
    with open(os.path.join(pipe, "bookseed.txt"), "w", encoding="utf-8") as f:
        f.write("")
    _write_json(
        os.path.join(pipe, "progress.json"),
        {
            "title": title,
            "language": req.language or "English",
            "source_terms": [],
            "context": req.gist or "",
            "total_chapters": 0,
            "completed_chapters": 0,
            "current_chapter": 1,
            "chapters": [],
        },
    )

    return {"bookname": bookname, "form": form, "title": title}


@app.get("/books/{bookname}")
def get_book_by_name(bookname: str) -> dict:
    """Return the book plan (book.json) for a book."""
    return _load_book_plan(bookname)


@app.put("/books/{bookname}")
def edit_book(bookname: str, req: EditBookRequest) -> dict:
    """Update editable metadata on a book's plan."""
    plan = _load_book_plan(bookname)
    updates = req.model_dump(exclude_unset=True)
    if "form" in updates and updates["form"] not in ("novel", "poetry"):
        raise HTTPException(status_code=400, detail="form must be 'novel' or 'poetry'")
    plan.update(updates)
    _save_book_plan(bookname, plan)

    # keep pipeline book.json in sync for a few mirrored fields
    model_path = os.path.join(_pipeline_dir(bookname), "book.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(_pipeline_dir(bookname), "model.json")
    if os.path.exists(model_path):
        model = _read_json(model_path)
        for key in ("book_long_title", "form", "language", "gist", "book_summary"):
            if key in updates:
                model[key] = updates[key]
        _write_json(model_path, model)
    return plan


# ---------------------------------------------------------------------------
# Chapter CRUD
# ---------------------------------------------------------------------------

@app.get("/books/{bookname}/chapters")
def list_chapters(bookname: str) -> list[dict]:
    plan = _load_book_plan(bookname)
    return plan.get("chapters", [])


@app.post("/books/{bookname}/chapters", status_code=201)
def add_chapter(bookname: str, req: ChapterInput) -> dict:
    """Add a chapter to the plan and scaffold its pipeline folder."""
    plan = _load_book_plan(bookname)
    chapters = plan.get("chapters", [])

    if req.chapter_index is not None:
        idx = req.chapter_index
        if any(str(c.get("chapter_index")) == str(idx) for c in chapters):
            raise HTTPException(
                status_code=409, detail=f"chapter '{idx}' already exists"
            )
    else:
        idx = max(
            (int(c.get("chapter_index", 0)) for c in chapters if str(c.get("chapter_index", "")).isdigit()),
            default=0,
        ) + 1

    title = req.chapter_title or str(idx)
    summary = req.chapter_summary or ""
    entry = {
        "chapter_index": idx,
        "name": str(idx),
        "word_target": req.word_target,
        "chapter_title": title,
        "chapter_summary": summary,
        "further_references": [],
    }
    chapters.append(entry)
    plan["chapters"] = chapters
    plan["chapter_count"] = len(chapters)
    _save_book_plan(bookname, plan)

    # pipeline book.json / bookseed.txt / progress.json
    pipe = _pipeline_dir(bookname)
    model_path = os.path.join(pipe, "book.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(pipe, "model.json")
    if os.path.exists(model_path):
        model = _read_json(model_path)
        model["chapter_count"] = len(chapters)
        model["source_terms"] = [c.get("chapter_title", str(c.get("chapter_index"))) for c in chapters]
        _write_json(model_path, model)

    with open(os.path.join(pipe, "bookseed.txt"), "w", encoding="utf-8") as f:
        for c in chapters:
            f.write(f"{c.get('chapter_title', c.get('chapter_index'))}\n")

    prog_path = os.path.join(pipe, "progress.json")
    if os.path.exists(prog_path):
        prog = _read_json(prog_path)
        prog["total_chapters"] = len(chapters)
        prog["source_terms"] = [c.get("chapter_title", str(c.get("chapter_index"))) for c in chapters]
        existing_nums = {c.get("chapter_number") for c in prog.get("chapters", [])}
        if str(idx) not in {str(n) for n in existing_nums}:
            prog.setdefault("chapters", []).append({
                "chapter_number": idx,
                "topic": title,
                "category": plan.get("generic", ""),
                "status": "pending",
                "file_path": f"chapters\\{idx}\\chapter.md",
                "completed_date": None,
            })
        _write_json(prog_path, prog)

    # chapter folder skeleton
    cd = _chapter_dir(bookname, idx)
    os.makedirs(os.path.join(cd, "history"), exist_ok=True)
    seg = os.path.join(cd, "segments", "1")
    for sub in ("writer", "editor", "translator"):
        os.makedirs(os.path.join(seg, sub), exist_ok=True)
    _write_json(
        os.path.join(cd, "chapter.json"),
        {
            "level": "chapter",
            "state": "scaffolded",
            "chapter_index": idx,
            "chapter_name": str(idx),
            "topic": title,
            "chapter_title": title,
            "chapter_summary": summary,
            "word_target": req.word_target,
            "segments": [1],
        },
    )
    _write_json(
        os.path.join(seg, "model.json"),
        {"level": "segment", "state": "scaffolded", "chapter_index": idx, "segment_index": 1},
    )
    with open(os.path.join(cd, "chapter.md"), "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{summary}\n")

    return entry


@app.get("/books/{bookname}/chapters/{chapter}")
def get_chapter(bookname: str, chapter: str) -> dict:
    """Return a chapter's metadata (model.json)."""
    plan = _load_book_plan(bookname)
    name = _resolve_chapter_identifier(plan, chapter)
    model_path = os.path.join(_chapter_dir(bookname, name), "chapter.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(_chapter_dir(bookname, name), "model.json")
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail=f"chapter '{chapter}' not found")
    return _read_json(model_path)


@app.get("/books/{bookname}/chapters/{chapter}/content", response_model=ChapterContent)
def get_chapter_content(bookname: str, chapter: str) -> ChapterContent:
    """Return a chapter's written content (chapter.md)."""
    plan = _load_book_plan(bookname)
    name = _resolve_chapter_identifier(plan, chapter)
    cd = _chapter_dir(bookname, name)
    path = os.path.join(cd, "chapter.md")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"chapter '{chapter}' content not found")
    with open(path, encoding="utf-8") as f:
        content = f.read()
    return ChapterContent(bookname=bookname, chapter=name, content=content)


@app.put("/books/{bookname}/chapters/{chapter}")
def edit_chapter(bookname: str, chapter: str, req: ChapterEditInput) -> dict:
    """Update chapter metadata and/or content."""
    plan = _load_book_plan(bookname)
    name = _resolve_chapter_identifier(plan, chapter)
    cd = _chapter_dir(bookname, name)
    if not os.path.isdir(cd):
        raise HTTPException(status_code=404, detail=f"chapter '{chapter}' not found")

    # update plan entry
    for c in plan.get("chapters", []):
        if str(c.get("chapter_index")) == name or str(c.get("name")) == name:
            if req.chapter_title is not None:
                c["chapter_title"] = req.chapter_title
            if req.chapter_summary is not None:
                c["chapter_summary"] = req.chapter_summary
            if req.word_target is not None:
                c["word_target"] = req.word_target
    _save_book_plan(bookname, plan)

    # update chapter metadata (chapter.json, falling back to model.json)
    model_path = os.path.join(cd, "chapter.json")
    if not os.path.exists(model_path):
        model_path = os.path.join(cd, "model.json")
    if os.path.exists(model_path):
        model = _read_json(model_path)
        if req.chapter_title is not None:
            model["chapter_title"] = req.chapter_title
            model["topic"] = req.chapter_title
        if req.chapter_summary is not None:
            model["chapter_summary"] = req.chapter_summary
        if req.word_target is not None:
            model["word_target"] = req.word_target
        _write_json(model_path, model)

    # update content if provided
    if req.content is not None:
        with open(os.path.join(cd, "chapter.md"), "w", encoding="utf-8") as f:
            f.write(req.content)

    return get_chapter(bookname, name)


@app.delete("/books/{bookname}/chapters/{chapter}", status_code=204)
def delete_chapter(bookname: str, chapter: str) -> None:
    """Delete a chapter from the plan and its pipeline folder."""
    plan = _load_book_plan(bookname)
    name = _resolve_chapter_identifier(plan, chapter)

    chapters = plan.get("chapters", [])
    kept = [c for c in chapters if str(c.get("chapter_index")) != name and str(c.get("name")) != name]
    if len(kept) == len(chapters):
        raise HTTPException(status_code=404, detail=f"chapter '{chapter}' not found")
    plan["chapters"] = kept
    plan["chapter_count"] = len(kept)
    _save_book_plan(bookname, plan)

    cd = _chapter_dir(bookname, name)
    if os.path.isdir(cd):
        shutil.rmtree(cd)

    # bookseed.txt
    pipe = _pipeline_dir(bookname)
    with open(os.path.join(pipe, "bookseed.txt"), "w", encoding="utf-8") as f:
        for c in kept:
            f.write(f"{c.get('chapter_title', c.get('chapter_index'))}\n")


@app.get("/books/{bookname}/versions/{version}/chapters/{chapter}/content", response_model=ChapterContent)
def get_chapter_content_by_version(bookname: str, version: str, chapter: str) -> ChapterContent:
    """Return a chapter's content from a specific published version."""
    ver_dir = os.path.join(_src_dir(bookname), version)
    if not os.path.isdir(ver_dir):
        raise HTTPException(status_code=404, detail=f"version '{version}' not found")
    ch_dir = os.path.join(ver_dir, "chapters", chapter)
    if not os.path.isdir(ch_dir):
        raise HTTPException(status_code=404, detail=f"chapter '{chapter}' not found in {version}")

    # prefer a language subfolder if present, else chapter.md directly
    content = None
    direct = os.path.join(ch_dir, "chapter.md")
    if os.path.exists(direct):
        with open(direct, encoding="utf-8") as f:
            content = f.read()
    else:
        for sub in os.listdir(ch_dir):
            sub_md = os.path.join(ch_dir, sub, "chapter.md")
            if os.path.isfile(sub_md):
                with open(sub_md, encoding="utf-8") as f:
                    content = f.read()
                break
    if content is None:
        raise HTTPException(status_code=404, detail=f"chapter '{chapter}' content not found in {version}")
    return ChapterContent(bookname=bookname, chapter=chapter, content=content)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
