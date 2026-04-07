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
    content_hash TEXT,
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
    ended_at TIMESTAMP,
    FOREIGN KEY (resume_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (jd_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_text TEXT,
    question_type TEXT,
    category TEXT,
    difficulty INTEGER,
    target_skills TEXT,
    evaluation_atoms TEXT,
    sequence_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    answer_text TEXT,
    atom_scores TEXT,
    overall_score REAL,
    feedback TEXT,
    follow_up_question TEXT,
    time_taken_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Fix 2.11: Session state persistence table
CREATE TABLE IF NOT EXISTS session_state (
    session_id TEXT PRIMARY KEY,
    question_tree TEXT,
    current_question TEXT,
    current_dag TEXT,
    follow_up_count INTEGER DEFAULT 0,
    question_counter INTEGER DEFAULT 0,
    session_history TEXT,
    skill_tracker_state TEXT,
    adaptive_state TEXT,
    metadata TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Fix 2.21: Normalized skill_atom_scores table
CREATE TABLE IF NOT EXISTS skill_atom_scores (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    atom_id TEXT NOT NULL,
    atom_name TEXT NOT NULL,
    category TEXT NOT NULL,
    score REAL NOT NULL,
    passed INTEGER NOT NULL,
    evaluated_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);
"""

# Fix 2.20: Index creation statements
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_session_id ON questions(session_id);
CREATE INDEX IF NOT EXISTS idx_answers_question_id ON answers(question_id);
CREATE INDEX IF NOT EXISTS idx_answers_session_id ON answers(session_id);
CREATE INDEX IF NOT EXISTS idx_atom_scores_user ON skill_atom_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_atom_scores_session ON skill_atom_scores(session_id);
CREATE INDEX IF NOT EXISTS idx_atom_scores_atom ON skill_atom_scores(atom_id);
CREATE INDEX IF NOT EXISTS idx_atom_scores_category ON skill_atom_scores(category);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);
CREATE INDEX IF NOT EXISTS idx_session_state_session ON session_state(session_id);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(SQLITE_DB_PATH)
    db.row_factory = aiosqlite.Row
    # Fix 2.18: Enable foreign key enforcement
    await db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db() -> None:
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.executescript(INDEXES)
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
    content_hash: str = "",
) -> str:
    doc_id = gen_id()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO documents (id, user_id, type, raw_text, parsed_data, content_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, user_id, doc_type, raw_text, json.dumps(parsed_data), content_hash),
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


async def get_document_by_hash(content_hash: str) -> Optional[dict]:
    """Get a document by its content hash (for caching)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM documents WHERE content_hash = ? LIMIT 1",
            (content_hash,),
        )
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


# === Session State Persistence (Fix 2.11-2.12) ===

async def save_session_state(
    session_id: str,
    question_tree: str,
    current_question: str,
    current_dag: str,
    follow_up_count: int,
    question_counter: int,
    session_history: str,
    skill_tracker_state: str,
    adaptive_state: str,
    metadata: str,
) -> None:
    """Persist session state to database for recovery."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO session_state
               (session_id, question_tree, current_question, current_dag,
                follow_up_count, question_counter, session_history,
                skill_tracker_state, adaptive_state, metadata, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(session_id) DO UPDATE SET
                 question_tree = excluded.question_tree,
                 current_question = excluded.current_question,
                 current_dag = excluded.current_dag,
                 follow_up_count = excluded.follow_up_count,
                 question_counter = excluded.question_counter,
                 session_history = excluded.session_history,
                 skill_tracker_state = excluded.skill_tracker_state,
                 adaptive_state = excluded.adaptive_state,
                 metadata = excluded.metadata,
                 updated_at = CURRENT_TIMESTAMP""",
            (session_id, question_tree, current_question, current_dag,
             follow_up_count, question_counter, session_history,
             skill_tracker_state, adaptive_state, metadata),
        )
        await db.commit()
    finally:
        await db.close()


async def get_session_state(session_id: str) -> Optional[dict]:
    """Get persisted session state for recovery."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM session_state WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    finally:
        await db.close()
    return None


async def delete_session_state(session_id: str) -> None:
    """Delete persisted session state after session ends."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM session_state WHERE session_id = ?", (session_id,))
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
    # Fix 2.5: Validate question_id is not None/empty before insertion
    if not question_id:
        raise ValueError("question_id cannot be None or empty when saving an answer")

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


# === Normalized Skill Atom Scores (Fix 2.21) ===

async def save_skill_atom_score(
    user_id: str,
    session_id: str,
    question_id: str,
    atom_id: str,
    atom_name: str,
    category: str,
    score: float,
    passed: bool,
) -> None:
    """Save an individual atom score to the normalized table."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO skill_atom_scores
               (id, user_id, session_id, question_id, atom_id, atom_name, category, score, passed, evaluated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (gen_id(), user_id, session_id, question_id, atom_id, atom_name,
             category, score, 1 if passed else 0, datetime.utcnow().isoformat()),
        )
        await db.commit()
    finally:
        await db.close()


async def get_skill_atom_scores_normalized(
    user_id: str = "default",
    session_id: Optional[str] = None,
) -> list[dict]:
    """Get atom scores from the normalized table, optionally filtered by session."""
    db = await get_db()
    try:
        if session_id:
            cursor = await db.execute(
                """SELECT atom_id, atom_name, category,
                          AVG(score) as avg_score, COUNT(*) as attempts,
                          SUM(passed) as times_passed
                   FROM skill_atom_scores
                   WHERE user_id = ? AND session_id = ?
                   GROUP BY atom_id, atom_name, category
                   ORDER BY category, atom_name""",
                (user_id, session_id),
            )
        else:
            cursor = await db.execute(
                """SELECT atom_id, atom_name, category,
                          AVG(score) as avg_score, COUNT(*) as attempts,
                          SUM(passed) as times_passed
                   FROM skill_atom_scores
                   WHERE user_id = ?
                   GROUP BY atom_id, atom_name, category
                   ORDER BY category, atom_name""",
                (user_id,),
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# === Analytics queries ===

async def get_session_history(user_id: str = "default", limit: int = 20) -> list[dict]:
    """Get session history with question counts. Uses indexed queries (Fix 2.24)."""
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
