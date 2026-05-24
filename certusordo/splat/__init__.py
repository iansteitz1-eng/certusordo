"""
certusordo.splat — the structured action receipt + hash chain.

A splat is a structured, scored, hash-chained receipt emitted at the
moment of an agent action. It is *not* a log line: every field is
load-bearing and gets indexed in production. The hash-chain anchors each
splat to the previous one so tampering is detectable.

Quick start:

    from certusordo import emit

    splat = emit(
        harness_source="claude_code",
        interface="tool_call",
        intent="read /etc/hosts and report the loopback line",
        action_summary="open /etc/hosts via read_file; return line matching 127.0.0.1",
        output_excerpt="127.0.0.1 localhost",
        tool_called="read_file",
    )

The returned `Splat` is already scored and gated. By default, splats are
emitted in-memory; pass `storage=` to persist. See
`certusordo.splat.SqliteStorage` for the bundled SQLite backend.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
import time
import uuid
from typing import Any, Protocol


@dataclasses.dataclass
class Splat:
    """A structured action receipt.

    All fields are load-bearing. `splat_id`, `self_hash`, and
    `created_at` are filled by `emit()`; you should not need to construct
    a `Splat` by hand outside of tests.
    """

    splat_id: str
    harness_source: str
    interface: str
    intent: str
    action_summary: str
    output_excerpt: str
    tool_called: str | None
    score: dict[str, float]
    composite_score: float
    co_gate: str
    prev_splat_hash: str | None
    self_hash: str
    created_at: float
    extra_meta: dict[str, Any]

    def to_json(self) -> str:
        """Canonical JSON serialization, sorted-keys for stable hashing."""
        return json.dumps(dataclasses.asdict(self), sort_keys=True)


def _hash_splat(splat: Splat) -> str:
    """Stable SHA-256 hash over value-bearing fields. Excludes
    `self_hash` itself to avoid a chicken-and-egg loop."""
    payload = json.dumps(
        {
            "id": splat.splat_id,
            "harness": splat.harness_source,
            "interface": splat.interface,
            "intent": splat.intent,
            "action": splat.action_summary,
            "output": splat.output_excerpt,
            "tool": splat.tool_called,
            "composite": splat.composite_score,
            "co_gate": splat.co_gate,
            "prev": splat.prev_splat_hash,
            "created": splat.created_at,
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class Storage(Protocol):
    """Pluggable storage backend protocol."""

    def latest_hash(self) -> str | None: ...
    def insert(self, splat: Splat) -> None: ...


class _MemoryStorage:
    """Default in-memory storage for ad-hoc scoring."""

    def __init__(self) -> None:
        self._splats: list[Splat] = []

    def latest_hash(self) -> str | None:
        return self._splats[-1].self_hash if self._splats else None

    def insert(self, splat: Splat) -> None:
        self._splats.append(splat)


class SqliteStorage:
    """Reference SQLite backend. The schema mirrors the Postgres
    production table on a single-file dev store."""

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS splat_log (
            splat_id        TEXT PRIMARY KEY,
            harness_source  TEXT NOT NULL,
            interface       TEXT NOT NULL,
            intent          TEXT NOT NULL,
            action_summary  TEXT NOT NULL,
            output_excerpt  TEXT NOT NULL,
            tool_called     TEXT,
            score_json      TEXT NOT NULL,
            composite_score REAL NOT NULL,
            co_gate         TEXT NOT NULL,
            prev_splat_hash TEXT,
            self_hash       TEXT NOT NULL,
            created_at      REAL NOT NULL,
            extra_meta      TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_gate ON splat_log(co_gate, created_at);
        CREATE INDEX IF NOT EXISTS ix_harness ON splat_log(harness_source, created_at);
    """

    def __init__(self, path: str = ":memory:") -> None:
        self.path = path
        with sqlite3.connect(self.path) as c:
            c.executescript(self.SCHEMA)

    def latest_hash(self) -> str | None:
        with sqlite3.connect(self.path) as c:
            row = c.execute(
                "SELECT self_hash FROM splat_log ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else None

    def insert(self, splat: Splat) -> None:
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO splat_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    splat.splat_id,
                    splat.harness_source,
                    splat.interface,
                    splat.intent,
                    splat.action_summary,
                    splat.output_excerpt,
                    splat.tool_called,
                    json.dumps(splat.score),
                    splat.composite_score,
                    splat.co_gate,
                    splat.prev_splat_hash,
                    splat.self_hash,
                    splat.created_at,
                    json.dumps(splat.extra_meta),
                ),
            )


_default_storage: Storage = _MemoryStorage()


def set_storage(storage: Storage) -> None:
    """Swap the global storage backend (e.g., to `SqliteStorage`)."""
    global _default_storage
    _default_storage = storage


def emit(
    harness_source: str,
    interface: str,
    intent: str,
    action_summary: str,
    output_excerpt: str,
    tool_called: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    storage: Storage | None = None,
) -> Splat:
    """Emit a single splat: build, score, hash-chain, persist, return.

    This is the only entry point you need to use. Pass `storage=` to use
    a non-default backend (SQLite, Postgres adapter, etc.).
    """
    # Import locally to avoid a circular import at module load.
    from certusordo.rubric import score as _score

    store = storage or _default_storage

    splat = Splat(
        splat_id=str(uuid.uuid4()),
        harness_source=harness_source,
        interface=interface,
        intent=intent,
        action_summary=action_summary,
        output_excerpt=output_excerpt[:500],
        tool_called=tool_called,
        score={},
        composite_score=0.0,
        co_gate="",
        prev_splat_hash=store.latest_hash(),
        self_hash="",
        created_at=time.time(),
        extra_meta=extra_meta or {},
    )
    splat.score, splat.composite_score, splat.co_gate = _score(splat)
    splat.self_hash = _hash_splat(splat)
    store.insert(splat)
    return splat
