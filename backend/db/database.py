"""SQLite async database layer."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import aiosqlite

from config import SQLITE_DB_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    type TEXT CHECK(type IN ('resume', 'job_description')),
    raw_text TEXT,
    parsed_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    resume_id TEXT,
    jd_id TEXT,
    mode TEXT CHECK(mode IN ('mock', 'prep', 'realtime')),
    status TEXT DEFAULT 'active',
    overall_score REAL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    question_text TEXT,
    question_type TEXT,
    category TEXT,
    difficulty INTEGER,
    target_skills TEXT,
    evaluation_atoms TEXT,
    sequence_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    question_id TEXT,
    session_id TEXT,
    answer_text TEXT,
    atom_scores TEXT,
    overall_score REAL,
    feedback TEXT,
    follow_up_question TEXT,
    time_taken_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS skill_atoms (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    atom_id TEXT,
    atom_label TEXT,
    category TEXT,
    cumulative_score REAL DEFAULT 0,
    attempt_count INTEGER DEFAULT 0,
    last_assessed TIMESTAMP,
    UNIQUE(user_id, atom_id)
);

CREATE TABLE IF NOT EXISTS prep_materials (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    questions TEXT,
    talking_points TEXT,
    weakness_analysis TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(SQLITE_DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
        # Ensure default user exists
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
            ("default", "Default User"),
        )
        await db.commit()
        logger.info("Database initialized at %s", SQLITE_DB_PATH)
    finally:
        await db.close()


def gen_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())[:12]


# === Document CRUD ===

async def save_document(
    doc_type: str,
    raw_text: str,
    parsed_data: dict,
    user_id: str = "default",
) -> str:
    doc_id = gen_id()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO documents (id, user_id, type, raw_text, parsed_data) VALUES (?, ?, ?, ?, ?)",
            (doc_id, user_id, doc_type, raw_text, json.dumps(parsed_data)),
        )
        await db.commit()
    finally:
        await db.close()
    return doc_id


async def get_document(doc_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "user_id": row["user_id"],
                "type": row["type"],
                "raw_text": row["raw_text"],
                "parsed_data": json.loads(row["parsed_data"]) if row["parsed_data"] else {},
                "created_at": row["created_at"],
            }
    finally:
        await db.close()
    return None


# === Session CRUD ===

async def create_session(
    resume_id: str,
    jd_id: str,
    mode: str,
    user_id: str = "default",
) -> str:
    session_id = gen_id()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO sessions (id, user_id, resume_id, jd_id, mode) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, resume_id, jd_id, mode),
        )
        await db.commit()
    finally:
        await db.close()
    return session_id


async def get_session(session_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)
    finally:
        await db.close()
    return None


async def update_session(session_id: str, **kwargs) -> None:
    db = await get_db()
    try:
        sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [session_id]
        await db.execute(f"UPDATE sessions SET {sets} WHERE id = ?", values)
        await db.commit()
    finally:
        await db.close()


# === Question CRUD ===

async def save_question(
    session_id: str,
    question_text: str,
    category: str,
    difficulty: int,
    target_skills: list[str],
    evaluation_atoms: dict,
    sequence: int,
) -> str:
    q_id = gen_id()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO questions (id, session_id, question_text, category, difficulty, target_skills, evaluation_atoms, sequence_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (q_id, session_id, question_text, category, difficulty, json.dumps(target_skills), json.dumps(evaluation_atoms), sequence),
        )
        await db.commit()
    finally:
        await db.close()
    return q_id


# === Answer CRUD ===

async def save_answer(
    question_id: str,
    session_id: str,
    answer_text: str,
    atom_scores: dict,
    overall_score: float,
    feedback: str,
    follow_up: str = "",
    time_taken: float = 0.0,
) -> str:
    a_id = gen_id()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO answers (id, question_id, session_id, answer_text, atom_scores, overall_score, feedback, follow_up_question, time_taken_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (a_id, question_id, session_id, answer_text, json.dumps(atom_scores), overall_score, feedback, follow_up, time_taken),
        )
        await db.commit()
    finally:
        await db.close()
    return a_id


# === Analytics queries ===

async def get_session_history(user_id: str = "default", limit: int = 20) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT s.*, COUNT(q.id) as question_count
               FROM sessions s LEFT JOIN questions q ON s.id = q.session_id
               WHERE s.user_id = ?
               GROUP BY s.id
               ORDER BY s.started_at DESC LIMIT ?""",
            (user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_skill_atom_scores(user_id: str = "default") -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM skill_atoms WHERE user_id = ? ORDER BY category, atom_label",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def upsert_skill_atom(
    user_id: str,
    atom_id: str,
    atom_label: str,
    category: str,
    score: float,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO skill_atoms (id, user_id, atom_id, atom_label, category, cumulative_score, attempt_count, last_assessed)
               VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
               ON CONFLICT(user_id, atom_id) DO UPDATE SET
                 cumulative_score = 0.3 * ? + 0.7 * cumulative_score,
                 attempt_count = attempt_count + 1,
                 last_assessed = CURRENT_TIMESTAMP""",
            (gen_id(), user_id, atom_id, atom_label, category, score, score),
        )
        await db.commit()
    finally:
        await db.close()
