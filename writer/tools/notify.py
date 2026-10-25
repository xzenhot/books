"""Decoupled notification logger.

A tiny publish/subscribe event bus with a durable append-only transport.

Design goals (no tight coupling):

- **Producers** (``tools/write.py``, ``tools/enrich.py``) call ``emit(...)``
  without knowing whether anyone is listening, or in which process.
- **Consumers** (e.g. ``app.py``) call ``subscribe(handler)`` to receive
  events in-process.
- **Cross-process transport.** Because ``app.py`` drives the engine through
  ``tools/book.py`` as a separate subprocess, every event is *also* appended
  to ``_logs/notifications.jsonl``. A consumer can tail that file to observe
  events raised in a child process. The file is the only coupling point, and
  both sides agree on it independently.

The logger is deliberately simple: no third-party packages, thread-safe, and
never lets a subscriber's error break the producer.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "_logs" / "notifications.jsonl"

# Well-known event kinds.
CHAPTER_WRITTEN = "chapter_written"
CHAPTER_ENRICHED = "chapter_enriched"


@dataclass
class Event:
    """One notification delivered to subscribers."""

    kind: str          # e.g. "chapter_written" / "chapter_enriched"
    bookname: str
    chapter: str       # chapter number or name
    title: str = ""
    message: str = ""
    ts: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "bookname": self.bookname,
            "chapter": self.chapter,
            "title": self.title,
            "message": self.message,
            "ts": self.ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Event":
        return cls(
            kind=str(data.get("kind", "")),
            bookname=str(data.get("bookname", "")),
            chapter=str(data.get("chapter", "")),
            title=str(data.get("title", "")),
            message=str(data.get("message", "")),
            ts=str(data.get("ts", "")),
        )


class Logger:
    """A subscriber registry plus a durable event transport."""

    def __init__(self) -> None:
        self._subscribers: list = []
        self._lock = threading.Lock()

    def subscribe(self, handler) -> "handler":
        """Register *handler(event)*; returns the handler for later unsubscribe."""
        with self._lock:
            self._subscribers.append(handler)
        return handler

    def unsubscribe(self, handler) -> None:
        with self._lock:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

    def notify(self, event: Event) -> None:
        # Deliver to in-process subscribers first; never let one subscriber
        # break delivery to the others.
        for handler in list(self._subscribers):
            try:
                handler(event)
            except Exception:
                pass
        self._persist(event)

    def _persist(self, event: Event) -> None:
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.as_dict(), ensure_ascii=False) + "\n")
        except OSError:
            # Persistence is best-effort; never fail the producer.
            pass


_logger = Logger()


def subscribe(handler):
    """Register a subscriber callback ``handler(event)``."""
    return _logger.subscribe(handler)


def unsubscribe(handler) -> None:
    """Remove a previously registered subscriber."""
    _logger.unsubscribe(handler)


def emit(kind: str, bookname: str, chapter, title: str = "",
         message: str = "") -> Event:
    """Publish one event to subscribers and the durable transport."""
    event = Event(
        kind=kind,
        bookname=bookname,
        chapter=str(chapter),
        title=title,
        message=message,
        ts=datetime.now(timezone.utc).isoformat(),
    )
    _logger.notify(event)
    return event


def read_log() -> list[Event]:
    """Return every event currently persisted to the transport, in order."""
    events: list[Event] = []
    if not LOG_PATH.is_file():
        return events
    try:
        for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(Event.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue
    except OSError:
        pass
    return events
