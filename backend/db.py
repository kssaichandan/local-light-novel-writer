"""Local SQLite storage. One file on disk, never leaves the machine.

Schema
------
projects : one novel project (taste profile, bible, outline, settings, status)
chapters : generated chapters + their per-chapter summary
arcs     : rolled-up arc summaries (hierarchical memory for very long stories)
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any, Optional

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL DEFAULT 'Untitled',
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL,
    model        TEXT NOT NULL,
    target_chapters INTEGER NOT NULL DEFAULT 100,
    chapters_per_arc INTEGER NOT NULL DEFAULT 10,
    status       TEXT NOT NULL DEFAULT 'new',  -- new|bible|outline|writing|done
    taste        TEXT NOT NULL DEFAULT '{}',   -- json
    bible        TEXT NOT NULL DEFAULT '{}',   -- json
    outline      TEXT NOT NULL DEFAULT '[]'    -- json (list of chapter beats)
);

CREATE TABLE IF NOT EXISTS chapters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number      INTEGER NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    UNIQUE(project_id, number)
);

CREATE TABLE IF NOT EXISTS arcs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number      INTEGER NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    UNIQUE(project_id, number)
);

CREATE TABLE IF NOT EXISTS volumes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number      INTEGER NOT NULL,
    summary     TEXT NOT NULL DEFAULT '',
    created_at  REAL NOT NULL,
    UNIQUE(project_id, number)
);

CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    number      INTEGER NOT NULL,            -- chapter the feedback is about
    data        TEXT NOT NULL DEFAULT '{}',  -- json (the raw feedback)
    created_at  REAL NOT NULL
);

-- Named, reusable taste profiles (the long-run 'learned taste'), global across novels.
CREATE TABLE IF NOT EXISTS taste_profiles (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL UNIQUE,
    taste          TEXT NOT NULL DEFAULT '{}',  -- json: the declared taste profile
    learned        TEXT NOT NULL DEFAULT '{}',  -- json: the evolving dials/lists
    feedback_count INTEGER NOT NULL DEFAULT 0,
    created_at     REAL NOT NULL,
    updated_at     REAL NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    # timeout + busy_timeout + WAL so the app's own concurrent writes (progressive autosave,
    # finalize, feedback, repair) wait for each other instead of failing with "database is locked".
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def init() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        # Migrations: add newer columns to existing projects tables.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(projects)")}
        if "learned" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN learned TEXT NOT NULL DEFAULT '{}'")
        if "arc_map" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN arc_map TEXT NOT NULL DEFAULT '[]'")
        if "volume_map" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN volume_map TEXT NOT NULL DEFAULT '[]'")
        if "state" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN state TEXT NOT NULL DEFAULT '{}'")
        if "use_scenes" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN use_scenes INTEGER NOT NULL DEFAULT 0")
        if "intro" not in cols:
            conn.execute("ALTER TABLE projects ADD COLUMN intro TEXT NOT NULL DEFAULT ''")


# ----------------------------------------------------------------------------- projects
def create_project(title: str, model: str, target_chapters: int, chapters_per_arc: int) -> int:
    now = time.time()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (title, created_at, updated_at, model, target_chapters, chapters_per_arc) "
            "VALUES (?,?,?,?,?,?)",
            (title, now, now, model, target_chapters, chapters_per_arc),
        )
        return cur.lastrowid


def _loads(raw, default):
    """Tolerant JSON decode — a single corrupt column must never make a project unopenable
    (so export/repair can still rescue the prose)."""
    try:
        v = json.loads(raw) if raw not in (None, "") else default
        return v if v is not None else default
    except (ValueError, TypeError):
        return default


def _row_to_project(row: sqlite3.Row) -> dict:
    p = dict(row)
    p["taste"] = _loads(p.get("taste"), {})
    p["bible"] = _loads(p.get("bible"), {})
    p["outline"] = _loads(p.get("outline"), [])
    p["learned"] = _loads(p.get("learned"), {})
    p["arc_map"] = _loads(p.get("arc_map"), [])
    p["volume_map"] = _loads(p.get("volume_map"), [])
    p["state"] = _loads(p.get("state"), {})
    p["use_scenes"] = bool(p.get("use_scenes", 0))
    return p


def get_project(project_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    return _row_to_project(row) if row else None


def list_projects() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT p.id, p.title, p.created_at, p.updated_at, p.model, "
            "       p.target_chapters, p.status, "
            "       (SELECT COUNT(*) FROM chapters c WHERE c.project_id = p.id) AS written "
            "FROM projects p ORDER BY p.updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_project(project_id: int, **fields: Any) -> None:
    if not fields:
        return
    fields["updated_at"] = time.time()
    for key in ("taste", "bible", "outline", "learned", "arc_map", "volume_map", "state"):
        if key in fields and not isinstance(fields[key], str):
            fields[key] = json.dumps(fields[key], ensure_ascii=False)
    cols = ", ".join(f"{k}=?" for k in fields)
    with _connect() as conn:
        conn.execute(f"UPDATE projects SET {cols} WHERE id=?", (*fields.values(), project_id))


def delete_project(project_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM projects WHERE id=?", (project_id,))


# ----------------------------------------------------------------------------- chapters
def save_chapter(project_id: int, number: int, title: str, content: str, summary: str) -> None:
    # On update, KEEP the existing summary when the incoming one is empty (autosave/partial writes
    # pass summary=""), so a good summary is never blanked and long-term memory isn't lost.
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chapters (project_id, number, title, content, summary, created_at) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(project_id, number) DO UPDATE SET "
            "title=excluded.title, content=excluded.content, "
            "summary=CASE WHEN excluded.summary <> '' THEN excluded.summary ELSE chapters.summary END",
            (project_id, number, title, content, summary, time.time()),
        )


def get_chapter(project_id: int, number: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM chapters WHERE project_id=? AND number=?", (project_id, number)
        ).fetchone()
    return dict(row) if row else None


def list_chapters(project_id: int, with_content: bool = False) -> list[dict]:
    cols = "id, number, title, summary, created_at" + (", content" if with_content else "")
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT {cols} FROM chapters WHERE project_id=? ORDER BY number", (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def chapter_count(project_id: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM chapters WHERE project_id=?", (project_id,)
        ).fetchone()
    return row["n"]


def recent_summaries(project_id: int, limit: int, before_number: int | None = None) -> list[dict]:
    """The last `limit` chapter summaries (chronological). If `before_number` is
    given, only chapters strictly before it — so regenerating chapter N never sees
    its own old summary."""
    q = "SELECT number, title, summary FROM chapters WHERE project_id=?"
    params: list = [project_id]
    if before_number is not None:
        q += " AND number < ?"
        params.append(before_number)
    q += " ORDER BY number DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in reversed(rows)]


# ----------------------------------------------------------------------------- feedback
def save_feedback(project_id: int, number: int, data: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO feedback (project_id, number, data, created_at) VALUES (?,?,?,?)",
            (project_id, number, json.dumps(data, ensure_ascii=False), time.time()),
        )


def list_feedback(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT number, data, created_at FROM feedback WHERE project_id=? ORDER BY id",
            (project_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["data"] = json.loads(d["data"])
        out.append(d)
    return out


# ----------------------------------------------------------------------------- taste profiles
def save_taste_profile(name: str, taste: dict, learned: dict, feedback_count: int) -> int:
    now = time.time()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO taste_profiles (name, taste, learned, feedback_count, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET taste=excluded.taste, learned=excluded.learned, "
            "feedback_count=excluded.feedback_count, updated_at=excluded.updated_at",
            (name, json.dumps(taste, ensure_ascii=False), json.dumps(learned, ensure_ascii=False),
             feedback_count, now, now),
        )
        return cur.lastrowid


def list_taste_profiles() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, feedback_count, updated_at FROM taste_profiles ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_taste_profile(profile_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM taste_profiles WHERE id=?", (profile_id,)).fetchone()
    if not row:
        return None
    p = dict(row)
    p["taste"] = json.loads(p["taste"])
    p["learned"] = json.loads(p["learned"])
    return p


def rename_taste_profile(profile_id: int, name: str) -> bool:
    """Rename a saved taste. Returns False if the new name is already taken."""
    with _connect() as conn:
        clash = conn.execute(
            "SELECT 1 FROM taste_profiles WHERE name=? AND id<>?", (name, profile_id)
        ).fetchone()
        if clash:
            return False
        conn.execute(
            "UPDATE taste_profiles SET name=?, updated_at=? WHERE id=?",
            (name, time.time(), profile_id),
        )
    return True


def delete_taste_profile(profile_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM taste_profiles WHERE id=?", (profile_id,))


# ----------------------------------------------------------------------------- arcs
def save_arc(project_id: int, number: int, summary: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO arcs (project_id, number, summary, created_at) VALUES (?,?,?,?) "
            "ON CONFLICT(project_id, number) DO UPDATE SET summary=excluded.summary",
            (project_id, number, summary, time.time()),
        )


def list_arcs(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT number, summary FROM arcs WHERE project_id=? ORDER BY number", (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ----------------------------------------------------------------------------- volumes (memory A)
def save_volume(project_id: int, number: int, summary: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO volumes (project_id, number, summary, created_at) VALUES (?,?,?,?) "
            "ON CONFLICT(project_id, number) DO UPDATE SET summary=excluded.summary",
            (project_id, number, summary, time.time()),
        )


def list_volumes(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT number, summary FROM volumes WHERE project_id=? ORDER BY number", (project_id,)
        ).fetchall()
    return [dict(r) for r in rows]
