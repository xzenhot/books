#!/usr/bin/env python3
"""Writer — a lightweight desktop front-end for the /book workflow.

The single entry point of the underlying engine is `tools/book.py`. This app
provides a tkinter desktop UI that:

  * lists books across workspaces/backlog, workspaces/pipeline, workspaces/published;
  * selects a book, a verb, and free-form arguments;
  * runs the command through `python tools/book.py <bookname> <verb> [args...]`;
  * streams stdout/stderr into a console pane (non-blocking).

No third-party packages are required — it uses only the Python standard library
(tkinter, subprocess, threading, json, pathlib). It never defines workflow
behavior of its own; it only forwards to `tools/book.py`, exactly like book.ps1.

Usage:
    python app.py            # open the GUI
    python app.py --list     # print available books and exit
"""

import argparse
import json
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

REPO_ROOT = Path(__file__).resolve().parent
BOOK_SCRIPT = REPO_ROOT / "tools" / "book.py"
PYTHON = sys.executable

# The verbs the engine (tools/book.py) actually dispatches.
# `init` and `backlog` are exposed via the dedicated "Create" button instead of
# the verb dropdown.
VERBS = [
    "layout", "scaffold", "enrich", "write", "publish",
    "preview", "review", "humanize",
]

# Verbs that also accept a "chapter" target for hinting purposes.
CHAPTER_VERBS = {"enrich", "write", "review", "humanize"}


def scan_books():
    """Return a sorted, deduplicated list of book names across the three roots."""
    names = set()
    for root in ("backlog", "pipeline", "published"):
        d = REPO_ROOT / "workspaces" / root
        if d.is_dir():
            for child in d.iterdir():
                if child.is_dir():
                    names.add(child.name)
    return sorted(names)


def book_details(bookname):
    """Return (states, form, chapter_count) for a book across the three roots.

    states: sorted list of roots the book exists in ('backlog', 'pipeline',
    'published'). form and chapter_count are read from the first available
    book.json (backlog → pipeline → published); both are None when absent.
    """
    states = []
    form = None
    chapter_count = None
    for root in ("backlog", "pipeline", "published"):
        d = REPO_ROOT / "workspaces" / root / bookname
        if not d.is_dir():
            continue
        states.append(root)
        if form is None:
            plan = d / "book.json"
            if plan.is_file():
                try:
                    data = json.loads(plan.read_text(encoding="utf-8-sig"))
                except (json.JSONDecodeError, OSError):
                    data = {}
                form = data.get("form")
                cc = data.get("chapter_count")
                if isinstance(cc, int):
                    chapter_count = cc
                elif isinstance(data.get("chapters"), list):
                    chapter_count = len(data["chapters"])
    return states, form, chapter_count


def list_books_text():
    lines = []
    for root in ("backlog", "pipeline", "published"):
        d = REPO_ROOT / "workspaces" / root
        if d.is_dir() and any(c.is_dir() for c in d.iterdir()):
            lines.append(f"== {root} ==")
            for child in sorted(d.iterdir()):
                if child.is_dir():
                    lines.append(f"  {child.name}")
    return "\n".join(lines)


GIST_EXAMPLES = (
    "Example (novel): বাংলার গৌরব, সেন যুগের রাজনীতি, দিল্লির বাঙালি যাত্রামঞ্চ, "
    "এবং যুবরাজ লক্ষ্মণ সেনের কনৌজ-অভিযানকে কেন্দ্র করে একটি বাংলা "
    "ঐতিহাসিক-কাল্পনিক উপন্যাস।\n\n"
    "Example (poetry): মনসামঙ্গলের সেই নারী বেহুলা, যে স্বামী লখিন্দরের মৃতদেহ "
    "নিয়ে মৃত্যুকে অস্বীকার করে ইন্দ্রের সভায় ন্যায়বিচার দাবি করেছিল, হাজার বছর "
    "পরেও তার প্রতিরোধের অন্তর্জগৎ হয়ে ফিরে আসে।"
)


class CreateBookDialog(tk.Toplevel):
    """A single modal form asking for book name, gist (textarea), and form."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create Book")
        self.result = None
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 10, "pady": 6}
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, **pad)

        # Name.
        ttk.Label(body, text="Book name:").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.name_var, width=40).grid(
            row=0, column=1, sticky="we", pady=(0, 8)
        )

        # Form.
        ttk.Label(body, text="Form:").grid(row=1, column=0, sticky="w")
        self.form_var = tk.StringVar(value="novel")
        form_combo = ttk.Combobox(
            body, textvariable=self.form_var, values=("novel", "poetry"),
            state="readonly", width=10,
        )
        form_combo.grid(row=1, column=1, sticky="w", pady=(0, 8))

        # Gist textarea with scrollbar.
        ttk.Label(body, text="Gist (min ~100 words):").grid(row=2, column=0, columnspan=2, sticky="w")
        gist_wrap = ttk.Frame(body)
        gist_wrap.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.gist_text = tk.Text(gist_wrap, width=52, height=10, wrap="word")
        gist_scroll = ttk.Scrollbar(gist_wrap, orient="vertical", command=self.gist_text.yview)
        self.gist_text.configure(yscrollcommand=gist_scroll.set)
        self.gist_text.pack(side="left", fill="both", expand=True)
        gist_scroll.pack(side="right", fill="y")

        # Examples hint.
        ex = tk.Label(body, text=GIST_EXAMPLES, justify="left", anchor="w",
                      wraplength=430, foreground="#666", font=("TkDefaultFont", 8))
        ex.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # Buttons.
        btns = ttk.Frame(body)
        btns.grid(row=5, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="Create", command=self._ok).pack(side="right")

        body.columnconfigure(1, weight=1)
        body.rowconfigure(3, weight=1)

        self.bind("<Escape>", lambda e: self._cancel())
        self.name_var.set(parent.book_var.get().strip())
        # Center over the parent.
        self.update_idletasks()
        x = parent.winfo_rootx() + 40
        y = parent.winfo_rooty() + 40
        self.geometry(f"+{x}+{y}")

    def _ok(self):
        name = self.name_var.get().strip()
        gist = self.gist_text.get("1.0", "end").strip()
        form = self.form_var.get().strip().lower() or "novel"
        if not name:
            messagebox.showwarning("Missing book", "Book name is required.", parent=self)
            return
        if form not in {"novel", "poetry"}:
            messagebox.showwarning("Invalid form", "Form must be 'novel' or 'poetry'.", parent=self)
            return
        if gist and len(gist.split()) < 5:
            proceed = messagebox.askyesno(
                "Short gist",
                "The gist is under 5 words. Continue anyway?",
                parent=self,
            )
            if not proceed:
                return
        self.result = (name, gist, form)
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class FilePickerDialog(tk.Toplevel):
    """An Explorer-like file browser: a tree view of folders/files, a content
    pane, and edit/save for text files.

    - Left pane is a ``ttk.Treeview`` showing the root and its folders/files as a
      navigable tree (folders expand to reveal children).
    - Single-clicking a file shows its content in the right pane.
    - A "Top" button returns the tree to the root folder.
    - "Edit" makes a text file editable; "Save" writes it back (UTF-8).
    - Double-clicking a file returns its absolute path via ``self.result`` and
      closes the dialog.
    """

    TEXT_EXTS = {".md", ".txt", ".json", ".py", ".ps1", ".yaml", ".yml", ".csv", ".log", ".html"}

    def __init__(self, parent, root, title="Select file"):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.root = Path(root).resolve()
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 6, "pady": 4}
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, **pad)

        # Left: Explorer-style tree.
        left = ttk.LabelFrame(pane, text=self.root.name)
        pane.add(left, weight=2)
        self.tree = ttk.Treeview(left, show="tree")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.tree.bind("<ButtonRelease-1>", self._on_single)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<<TreeviewOpen>>", self._on_open)

        # Right: content preview / editor.
        right = ttk.LabelFrame(pane, text="Content")
        pane.add(right, weight=3)
        self.preview = tk.Text(right, wrap="word",
                               background="#101418", foreground="#d8dee9",
                               font=("Consolas", 9))
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=scroll.set)
        self.preview.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scroll.pack(side="right", fill="y", pady=4)

        # Buttons.
        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        ttk.Button(bar, text="Top", command=self._go_top).pack(side="left")
        ttk.Button(bar, text="Edit", command=self._edit).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Save", command=self._save).pack(side="left", padx=(6, 0))
        ttk.Button(bar, text="Cancel", command=self._cancel).pack(side="right")
        self.status_var = tk.StringVar(value="Double-click a file to select it.")
        ttk.Label(bar, textvariable=self.status_var, anchor="w").pack(side="left", padx=(12, 0))

        # State: currently displayed/editable file.
        self._current_file = None
        self._editing = False

        self._populate()
        self.geometry("960x600")
        self.update_idletasks()
        x = parent.winfo_rootx() + 20
        y = parent.winfo_rooty() + 20
        self.geometry(f"+{x}+{y}")

    # -- Tree population ---------------------------------------------------
    def _populate(self):
        self.tree.delete(*self.tree.get_children())
        if not self.root.is_dir():
            self.status_var.set(f"Not a directory: {self.root}")
            return
        self._root_iid = self.tree.insert("", "end", text=str(self.root), open=True)
        self._fill_dir(self._root_iid, self.root)

    def _fill_dir(self, parent_iid, directory):
        # Insert a child folder node (lazy-populated) for every subdirectory,
        # and a file leaf for every file.
        for child in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.is_dir():
                node = self.tree.insert(parent_iid, "end", text=child.name, open=False)
                self.tree.insert(node, "end", text="")  # placeholder for lazy load
            else:
                self.tree.insert(parent_iid, "end", text=child.name)

    def _on_open(self, event):
        node = self.tree.focus()
        path = self._node_path(node)
        if path is None or not path.is_dir():
            return
        # Replace the placeholder with the folder's real children.
        self.tree.delete(*self.tree.get_children(node))
        self._fill_dir(node, path)

    def _node_path(self, node):
        """Reconstruct the absolute path of a tree node from its ancestors."""
        if not node:
            return None
        parts = []
        current = node
        while current:
            parts.append(self.tree.item(current, "text"))
            current = self.tree.parent(current)
        parts = parts[::-1]
        # First part is the root (already absolute); join the rest.
        if not parts:
            return None
        path = Path(parts[0])
        for p in parts[1:]:
            path = path / p
        return path

    # -- Navigation / selection --------------------------------------------
    def _on_single(self, event):
        node = self.tree.identify_row(event.y)
        if not node:
            return
        path = self._node_path(node)
        if path is not None and path.is_file():
            self._copy_rel(path)
            self._show(path)

    def _on_double(self, event):
        node = self.tree.identify_row(event.y)
        if not node:
            return
        path = self._node_path(node)
        if path is not None and path.is_file():
            self.result = str(path)
            self.destroy()

    def _copy_rel(self, path):
        """Copy the path relative to the dialog root to the clipboard."""
        try:
            rel = path.relative_to(self.root).as_posix()
        except ValueError:
            rel = path.as_posix()
        self.clipboard_clear()
        self.clipboard_append(rel)

    def _go_top(self):
        self._current_file = None
        self._editing = False
        self._set_preview("", editable=False)
        self._populate()
        self.status_var.set("Showing root.")

    # -- Content display / editing -----------------------------------------
    def _show(self, path):
        self._current_file = path
        self._editing = False
        try:
            if path.suffix.lower() in self.TEXT_EXTS:
                text = path.read_text(encoding="utf-8", errors="replace")
            else:
                text = "(binary file — no preview)"
        except OSError as e:
            text = f"(cannot read: {e})"
        self._set_preview(text, editable=False)
        self.status_var.set(str(path))

    def _edit(self):
        if self._current_file is None:
            messagebox.showinfo("Edit", "Select a file first.", parent=self)
            return
        if self._current_file.suffix.lower() not in self.TEXT_EXTS:
            messagebox.showwarning("Edit", "This is not a text file.", parent=self)
            return
        self._editing = True
        self._set_preview(self.preview.get("1.0", "end-1c"), editable=True)
        self.status_var.set(f"Editing: {self._current_file}")

    def _save(self):
        if self._current_file is None:
            messagebox.showinfo("Save", "Nothing to save.", parent=self)
            return
        if not self._editing:
            return
        try:
            self._current_file.write_text(
                self.preview.get("1.0", "end-1c"), encoding="utf-8"
            )
        except OSError as e:
            messagebox.showerror("Save", f"Could not save: {e}", parent=self)
            return
        self._editing = False
        self._set_preview(self.preview.get("1.0", "end-1c"), editable=False)
        self.status_var.set(f"Saved: {self._current_file}")

    def _set_preview(self, text, editable):
        self.preview.config(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.config(state="normal" if editable else "disabled")

    def _cancel(self):
        self.result = None
        self.destroy()


class WriterApp(tk.Tk):
    """The tkinter desktop application."""

    def __init__(self):
        super().__init__()
        self.title("Writer — /book Desktop")
        self.geometry("880x640")
        self._proc = None

        self._build_ui()
        self._refresh_books()

    # -- UI construction ---------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}

        # Top: command builder.
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Book:").grid(row=0, column=0, sticky="w")
        self.book_var = tk.StringVar()
        self.book_combo = ttk.Combobox(
            top, textvariable=self.book_var, state="normal", width=18
        )
        self.book_combo.grid(row=0, column=1, sticky="w", padx=4)
        self.book_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_verb_hint())

        ttk.Label(top, text="Verb:").grid(row=0, column=2, sticky="w", padx=(12, 0))
        self.verb_var = tk.StringVar(value="scaffold")
        self.verb_combo = ttk.Combobox(
            top, textvariable=self.verb_var, values=VERBS, state="readonly", width=12
        )
        self.verb_combo.grid(row=0, column=3, sticky="w", padx=4)
        self.verb_combo.bind("<<ComboboxSelected>>", lambda e: self._on_verb_change())

        ttk.Label(top, text="Args:").grid(row=0, column=4, sticky="w", padx=(12, 0))
        self.args_var = tk.StringVar()
        self.args_entry = ttk.Entry(top, textvariable=self.args_var, width=34)
        self.args_entry.grid(row=0, column=5, sticky="we", padx=4)
        self.args_entry.bind("<Return>", lambda e: self.run())

        self.run_btn = ttk.Button(top, text="Run", command=self.run)
        self.run_btn.grid(row=0, column=6, padx=4)
        self.refresh_btn = ttk.Button(top, text="Refresh", command=self._refresh_books)
        self.refresh_btn.grid(row=0, column=7, padx=4)

        top.columnconfigure(5, weight=1)

        # Hint label.
        self.hint_var = tk.StringVar()
        ttk.Label(self, textvariable=self.hint_var, foreground="#666").pack(
            anchor="w", **pad
        )

        # Books list + console split.
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True, **pad)

        books_frame = ttk.LabelFrame(pane, text="Books")
        pane.add(books_frame, weight=1)
        self.books_tree = ttk.Treeview(books_frame, show="tree")
        self.books_tree.pack(fill="both", expand=True, padx=4, pady=4)
        self.books_tree.bind("<<TreeviewSelect>>", lambda e: self._on_book_select())

        console_frame = ttk.LabelFrame(pane, text="Output")
        pane.add(console_frame, weight=3)

        # Clear button above the console.
        clear_bar = ttk.Frame(console_frame)
        clear_bar.pack(fill="x", padx=4, pady=(4, 0))
        self.create_btn = ttk.Button(clear_bar, text="Create", command=self.create)
        self.create_btn.pack(side="left")
        self.browse_btn = ttk.Button(clear_bar, text="Browse", command=self.browse)
        self.browse_btn.pack(side="left", padx=(6, 0))
        self.close_btn = ttk.Button(clear_bar, text="Close", command=self.destroy)
        self.close_btn.pack(side="right")
        self.clear_btn = ttk.Button(clear_bar, text="Clear", command=self.clear_console)
        self.clear_btn.pack(side="right", padx=(0, 6))

        # Console with a vertical scrollbar.
        text_wrap = ttk.Frame(console_frame)
        text_wrap.pack(fill="both", expand=True, padx=4, pady=4)

        self.console = tk.Text(text_wrap, state="disabled", wrap="word",
                               background="#101418", foreground="#d8dee9",
                               font=("Consolas", 9))
        console_scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=self.console.yview)
        self.console.configure(yscrollcommand=console_scroll.set)
        self.console.pack(side="left", fill="both", expand=True)
        console_scroll.pack(side="right", fill="y")

        # Indeterminate progress bar (shown while a command runs).
        self.progress = ttk.Progressbar(self, mode="indeterminate")

        # Status bar.
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self.status_label.pack(fill="x", **pad)

    # -- Helpers ------------------------------------------------------------
    def _refresh_books(self):
        self._books = scan_books()
        self.books_tree.delete(*self.books_tree.get_children())
        for root in ("backlog", "pipeline", "published"):
            d = REPO_ROOT / "workspaces" / root
            if not d.is_dir():
                continue
            children = sorted(
                c.name for c in d.iterdir() if c.is_dir()
            )
            parent = self.books_tree.insert("", "end", text=root, open=True)
            for name in children:
                # Unique iid (book may appear under several categories).
                self.books_tree.insert(parent, "end", iid=f"{root}::{name}", text=name)
        current = self.book_var.get()
        if current in self._books:
            self.book_combo["values"] = self._books
        else:
            self.book_combo["values"] = self._books
            if self._books:
                self.book_var.set(self._books[0])
        self._refresh_verb_hint()

    def _on_book_select(self):
        sel = self.books_tree.selection()
        if not sel:
            return
        book = self.books_tree.item(sel[0], "text")
        # Ignore category nodes (backlog/pipeline/published) — only select books.
        if book in ("backlog", "pipeline", "published"):
            return
        self.book_var.set(book)
        self._show_book_status(book)
        self._prefill_args()

    def _on_verb_change(self):
        self._refresh_verb_hint()
        self._prefill_args()

    def _prefill_args(self):
        """Pre-fill the argument field based on the selected verb (default '*')."""
        verb = self.verb_var.get().strip()
        if verb in CHAPTER_VERBS:
            self.args_var.set("*")
        else:
            self.args_var.set("")

    def _show_book_status(self, book):
        """Display book details in the status bar."""
        states, form, chapter_count = book_details(book)
        state_txt = ", ".join(states) if states else "none"
        form_txt = form or "?"
        count_txt = chapter_count if chapter_count is not None else "?"
        self.status_var.set(
            f"Selected Book: {book} | State: {state_txt} | Form: {form_txt} | "
            f"Chapter Count: {count_txt}"
        )

    def _refresh_verb_hint(self):
        book = self.book_var.get()
        verb = self.verb_var.get()
        if verb in CHAPTER_VERBS:
            self.hint_var.set(
                f"Args for '{verb}': a chapter scope — 'all', '1-5', '2', or '*' "
                f"(e.g. {book} {verb} all)"
            )
        elif verb == "scaffold":
            self.hint_var.set(
                "Args for 'scaffold': optional chapter count and form "
                "(e.g. scaffold 22 novel). Form defaults to the book plan."
            )
        elif verb == "layout":
            self.hint_var.set(
                "Args for 'layout': optional chapter count and form "
                "(e.g. layout 22 novel)."
            )
        elif verb in ("publish", "preview", "review", "humanize"):
            self.hint_var.set(f"Args for '{verb}': optional scope/language. Leave blank for default.")
        else:
            self.hint_var.set("")

    # -- Run ----------------------------------------------------------------
    def run(self):
        if self._proc is not None and self._proc.poll() is None:
            messagebox.showinfo("Busy", "A command is already running.")
            return
        book = self.book_var.get().strip()
        verb = self.verb_var.get().strip()
        args_text = self.args_var.get().strip()
        if not book:
            messagebox.showwarning("Missing book", "Select or type a book name.")
            return
        if not verb:
            messagebox.showwarning("Missing verb", "Choose a verb.")
            return

        args = [t for t in args_text.split() if t]
        self._launch([book, verb, *args])

    def create(self):
        """Open a single form (name, gist textarea, form), then run `init`."""
        if self._proc is not None and self._proc.poll() is None:
            messagebox.showinfo("Busy", "A command is already running.")
            return
        dialog = CreateBookDialog(self)
        self.wait_window(dialog)  # block until the dialog is closed
        result = dialog.result
        if result is None:
            return
        name, gist, form = result
        args = []
        if gist:
            # The gist is passed as a single argv element (list-based Popen, no
            # shell), so spaces/newlines are preserved without needing quotes.
            args.append(gist)
        args.append(form)
        self.book_var.set(name)
        self._launch([name, "init", *args], refresh_books=True)

    def browse(self):
        """Open the file-selection dialog rooted at the repository, and show the
        chosen file path in the console."""
        dialog = FilePickerDialog(self, REPO_ROOT, title="Select file")
        self.wait_window(dialog)
        path = dialog.result
        if path:
            self._append_console(f"\nSelected file: {path}\n")
            self.status_var.set(f"Selected: {path}")
        else:
            self.status_var.set("Browse cancelled.")

    def _launch(self, argv, refresh_books=False):
        cmd = [PYTHON, str(BOOK_SCRIPT), *argv]
        self._refresh_after = refresh_books
        # Quote any argument containing whitespace for the console echo only;
        # the real argv is passed verbatim to subprocess (list-based, no shell).
        display = " ".join(
            f'"{a}"' if any(c.isspace() for c in a) else a for a in cmd
        )
        self._append_console(f"\n> {display}\n")
        self.status_var.set(f"Running: {' '.join(argv)}")
        self.run_btn.config(state="disabled")
        self.create_btn.config(state="disabled")
        self._show_progress()
        thread = threading.Thread(target=self._run_worker, args=(cmd,), daemon=True)
        thread.start()

    def _run_worker(self, cmd):
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            self._proc = proc
            for line in proc.stdout:
                self.after(0, self._append_console, line)
            proc.wait()
            code = proc.returncode
            self.after(0, self._on_done, code)
        except Exception as e:  # noqa: BLE001
            self.after(0, self._on_error, str(e))
        finally:
            self._proc = None

    def _on_done(self, code):
        self.run_btn.config(state="normal")
        self.create_btn.config(state="normal")
        self._hide_progress()
        if code == 0 and getattr(self, "_refresh_after", False):
            self._refresh_books()
            self._refresh_after = False
        self.status_var.set(f"Finished (exit {code})." if code == 0 else f"Failed (exit {code}).")
        self._append_console(f"\n[exit {code}]\n")

    def _on_error(self, msg):
        self.run_btn.config(state="normal")
        self.create_btn.config(state="normal")
        self._hide_progress()
        self.status_var.set(f"Error: {msg}")
        self._append_console(f"\n[error] {msg}\n")

    def _show_progress(self):
        self.progress.pack(fill="x", padx=6, pady=(0, 2), before=self.status_label)
        # Force the widget to be realized/mapped before starting the animation,
        # otherwise start() may not begin the indeterminate cycle.
        self.update_idletasks()
        self.progress.start(12)

    def _hide_progress(self):
        self.progress.stop()
        self.progress.pack_forget()

    def _append_console(self, text):
        self.console.config(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.config(state="disabled")

    def clear_console(self):
        """Clear the output console pane."""
        self.console.config(state="normal")
        self.console.delete("1.0", "end")
        self.console.config(state="disabled")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Writer desktop app for tools/book.py.")
    parser.add_argument("--list", action="store_true", help="Print available books and exit.")
    args = parser.parse_args(argv)

    if args.list:
        print(list_books_text())
        return 0

    if not BOOK_SCRIPT.is_file():
        print(f"Error: engine not found at {BOOK_SCRIPT}", file=sys.stderr)
        return 1

    app = WriterApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
