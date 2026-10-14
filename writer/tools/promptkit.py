#!/usr/bin/env python3
"""promptkit.py — Shared loader for the layout "dataset" template files.

The writer framework stores its prompts, schemas, and form guidance as plain
files under a ``layout/`` tree (see ``.framework/templates/backlog/v1/layout/``).
Those files are the *dataset*: the single source of truth for prompt text. This
module reads them and turns them into the prompt strings the tools send to
Ollama, so no tool embeds prompt text inline in its own source.

Two layout sources are supported:

* **Framework source** — ``.framework/templates/backlog/v1/layout/``. Used by the
  backlog-phase tools (``book.py``, ``expand.py``) that run before the pipeline
  is scaffolded.
* **Per-book pipeline** — ``workspaces/pipeline/<bookname>/layout/``. Used by the
  pipeline-phase engines (``enrich.py``, ``write.py``) that read the book's own
  cloned copy.

Placeholders in templates use ``{name}`` tokens and are filled by
:func:`render`, which replaces each token literally (so values containing braces
are safe).
"""

from __future__ import annotations

import json
from pathlib import Path


def framework_layout_dir(repo_root: Path) -> Path:
    """Return the framework's source layout dataset tree."""
    return Path(repo_root) / ".framework" / "templates" / "backlog" / "v1" / "layout"


def resolve_layout_dir(bookname: str, repo_root: Path) -> Path:
    """Return the book's own pipeline layout dataset tree."""
    return Path(repo_root) / "workspaces" / "pipeline" / bookname / "layout"


def resolve_template_dir(layout_dir: Path, phase: str, form: str | None = None) -> Path:
    """Resolve a phase folder inside a layout tree: ``layout/{phase}[-{form}]/``."""
    name = f"{phase}-{form}" if form else phase
    return Path(layout_dir) / name


def load_text(path: Path) -> str:
    """Read a template text file, tolerating a UTF-8 BOM."""
    return Path(path).read_text(encoding="utf-8-sig")


def load_json(path: Path):
    """Read a template JSON file (tolerating a UTF-8 BOM)."""
    return json.loads(load_text(path))


def render(template: str, **values) -> str:
    """Substitute ``{name}`` placeholders with values (safe for values containing braces)."""
    result = template
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    return result


class PromptSet:
    """Load a folder of template files (a dataset) into callable accessors.

    Example::

        ps = PromptSet(layout_dir, "book")            # reads layout/book/
        system = ps.text("layout_system_prompt.md")
        schema = ps.text("batch_chapter_schema.json")
    """

    def __init__(self, layout_dir: Path, phase: str, form: str | None = None):
        self._dir = resolve_template_dir(Path(layout_dir), phase, form)

    @property
    def dir(self) -> Path:
        """The resolved template folder backing this set."""
        return self._dir

    def text(self, filename: str) -> str:
        """Read a text template file from the set's folder."""
        path = self._dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing template file: {path}")
        return load_text(path)

    def json(self, filename: str):
        """Read a JSON template file from the set's folder."""
        return json.loads(self.text(filename))
