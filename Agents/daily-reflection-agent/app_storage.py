from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent.resolve()
DB_PATH = ROOT / "data" / "reflection_agent.db"


DEFAULT_GOALS = [
    {"area": "AI career", "target": "Create visible AI project proof every week."},
    {"area": "Fitness", "target": "Protect energy with simple movement and recovery."},
    {"area": "Discipline", "target": "Turn intentions into small finished reps."},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def write_with_retry(callback, attempts: int = 4):
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(attempts):
        try:
            with connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                result = callback(connection)
                connection.commit()
                return result
        except sqlite3.OperationalError as exc:
            last_error = exc
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
            time.sleep(0.12 * (attempt + 1))
    raise last_error or sqlite3.OperationalError("SQLite write failed.")


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS reflections (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                day TEXT NOT NULL,
                notes TEXT NOT NULL,
                score INTEGER NOT NULL,
                label TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                pattern TEXT NOT NULL,
                challenge TEXT NOT NULL,
                tomorrow TEXT NOT NULL,
                score_reason TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL DEFAULT '',
                rag_mode TEXT NOT NULL DEFAULT '',
                rag_used INTEGER NOT NULL DEFAULT 0,
                rag_debug TEXT NOT NULL DEFAULT '[]',
                builder_signal INTEGER NOT NULL DEFAULT 0,
                fitness_signal INTEGER NOT NULL DEFAULT 0,
                comfort_signal INTEGER NOT NULL DEFAULT 0,
                emotional_signal INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_reflections_day ON reflections(day);
            CREATE INDEX IF NOT EXISTS idx_reflections_created_at ON reflections(created_at);

            CREATE TABLE IF NOT EXISTS promise_status (
                reflection_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                area TEXT NOT NULL,
                target TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        ensure_column(connection, "reflections", "builder_signal", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "reflections", "fitness_signal", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "reflections", "comfort_signal", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "reflections", "emotional_signal", "INTEGER NOT NULL DEFAULT 0")

        goal_count = connection.execute("SELECT COUNT(*) FROM goals").fetchone()[0]
        if goal_count == 0:
            timestamp = now_iso()
            connection.executemany(
                """
                INSERT INTO goals (id, area, target, active, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                """,
                [
                    (str(uuid.uuid4()), item["area"], item["target"], timestamp, timestamp)
                    for item in DEFAULT_GOALS
                ],
            )


def row_to_reflection(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "date": row["created_at"],
        "day": row["day"],
        "notes": row["notes"],
        "score": row["score"],
        "label": row["label"],
        "title": row["title"],
        "summary": row["summary"],
        "pattern": row["pattern"],
        "challenge": row["challenge"],
        "tomorrow": row["tomorrow"],
        "scoreReason": row["score_reason"],
        "source": row["source"],
        "model": row["model"],
        "ragMode": row["rag_mode"],
        "ragUsed": bool(row["rag_used"]),
        "ragDebug": json.loads(row["rag_debug"] or "[]"),
        "builderSignal": bool(row["builder_signal"]),
        "fitnessSignal": bool(row["fitness_signal"]),
        "comfortSignal": bool(row["comfort_signal"]),
        "emotionalSignal": bool(row["emotional_signal"]),
    }


def infer_signals(payload: dict[str, Any]) -> dict[str, bool]:
    text = f"{payload.get('notes', '')} {payload.get('summary', '')} {payload.get('pattern', '')} {payload.get('challenge', '')}".lower()
    comfort_negative = any(
        phrase in text
        for phrase in [
            "avoided distractions",
            "avoid distractions",
            "did not scroll",
            "didn't scroll",
            "no scrolling",
            "avoided scrolling",
        ]
    )
    return {
        "builderSignal": bool(payload.get("builderSignal")) or any(word in text for word in ["ai", "agent", "code", "github", "project", "build", "shipped"]),
        "fitnessSignal": bool(payload.get("fitnessSignal")) or any(word in text for word in ["walk", "workout", "gym", "exercise", "fitness", "sleep", "mobility"]),
        "comfortSignal": bool(payload.get("comfortSignal")) or (
            not comfort_negative
            and any(word in text for word in ["comfort zone", "procrastinat", "later", "scroll", "watched video", "course instead", "avoided building"])
        ),
        "emotionalSignal": bool(payload.get("emotionalSignal")) or any(word in text for word in ["stress", "anxiety", "lonely", "burnout", "confidence", "emotion", "tired"]),
    }


def list_reflections(limit: int = 60) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM reflections
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_reflection(row) for row in rows]


def save_reflection(payload: dict[str, Any]) -> dict[str, Any]:
    reflection_id = str(payload.get("id") or uuid.uuid4())
    created_at = str(payload.get("date") or now_iso())
    day = str(payload.get("day") or created_at[:10])
    rag_debug = payload.get("ragDebug") if isinstance(payload.get("ragDebug"), list) else []
    signals = infer_signals(payload)

    def write(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO reflections (
                id, created_at, day, notes, score, label, title, summary, pattern,
                challenge, tomorrow, score_reason, source, model, rag_mode, rag_used, rag_debug,
                builder_signal, fitness_signal, comfort_signal, emotional_signal
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reflection_id,
                created_at,
                day,
                str(payload.get("notes", ""))[:12000],
                int(payload.get("score") or 60),
                str(payload.get("label", ""))[:100],
                str(payload.get("title", ""))[:180],
                str(payload.get("summary", ""))[:1200],
                str(payload.get("pattern", ""))[:900],
                str(payload.get("challenge", ""))[:900],
                str(payload.get("tomorrow", ""))[:400],
                str(payload.get("scoreReason", ""))[:700],
                str(payload.get("source", ""))[:80],
                str(payload.get("model", ""))[:160],
                str(payload.get("ragMode", ""))[:40],
                1 if payload.get("ragUsed") else 0,
                json.dumps(rag_debug, ensure_ascii=True),
                1 if signals["builderSignal"] else 0,
                1 if signals["fitnessSignal"] else 0,
                1 if signals["comfortSignal"] else 0,
                1 if signals["emotionalSignal"] else 0,
            ),
        )

    write_with_retry(write)
    saved = list_reflections(limit=1)
    return saved[0] if saved else payload


def list_promise_status() -> dict[str, str]:
    with connect() as connection:
        rows = connection.execute("SELECT reflection_id, status FROM promise_status").fetchall()
    return {row["reflection_id"]: row["status"] for row in rows}


def set_promise_status(reflection_id: str, status: str) -> None:
    if status not in {"kept", "missed"}:
        raise ValueError("Promise status must be kept or missed.")
    def write(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO promise_status (reflection_id, status, updated_at)
            VALUES (?, ?, ?)
            """,
            (reflection_id, status, now_iso()),
        )
    write_with_retry(write)


def list_goals() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, area, target, active, created_at, updated_at FROM goals ORDER BY created_at"
        ).fetchall()
    return [
        {
            "id": row["id"],
            "area": row["area"],
            "target": row["target"],
            "active": bool(row["active"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        for row in rows
    ]


def replace_goals(goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timestamp = now_iso()
    clean_goals = [
        {
            "id": str(item.get("id") or uuid.uuid4()),
            "area": str(item.get("area", "")).strip()[:80],
            "target": str(item.get("target", "")).strip()[:300],
        }
        for item in goals
        if str(item.get("area", "")).strip() and str(item.get("target", "")).strip()
    ][:8]
    def write(connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM goals")
        connection.executemany(
            """
            INSERT INTO goals (id, area, target, active, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            [
                (item["id"], item["area"], item["target"], timestamp, timestamp)
                for item in clean_goals
            ],
        )
    write_with_retry(write)
    return list_goals()


def analytics() -> dict[str, Any]:
    reflections = list(reversed(list_reflections(limit=60)))
    promise_status = list_promise_status()
    if not reflections:
        return {
            "reflectionCount": 0,
            "averageScore": 0,
            "promiseRate": 0,
            "builderDays": 0,
            "fitnessDays": 0,
            "comfortDays": 0,
            "latestPromise": "",
            "trend": [],
        }

    recent = reflections[-14:]
    average = round(sum(int(item.get("score") or 0) for item in recent) / len(recent))
    kept = sum(1 for status in promise_status.values() if status == "kept")
    marked = sum(1 for status in promise_status.values() if status in {"kept", "missed"})
    builder_days = sum(1 for item in recent if item.get("builderSignal"))
    fitness_days = sum(1 for item in recent if item.get("fitnessSignal"))
    comfort_days = sum(1 for item in recent if item.get("comfortSignal"))
    return {
        "reflectionCount": len(reflections),
        "averageScore": average,
        "promiseRate": round((kept / marked) * 100) if marked else 0,
        "builderDays": builder_days,
        "fitnessDays": fitness_days,
        "comfortDays": comfort_days,
        "latestPromise": reflections[-1].get("tomorrow", ""),
        "trend": [{"day": item.get("day", ""), "score": item.get("score", 0)} for item in recent],
    }


def export_all() -> dict[str, Any]:
    return {
        "exportedAt": now_iso(),
        "database": str(DB_PATH),
        "reflections": list_reflections(limit=1000),
        "promiseStatus": list_promise_status(),
        "goals": list_goals(),
    }


def clear_all() -> None:
    def write(connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM promise_status")
        connection.execute("DELETE FROM reflections")
        connection.execute("DELETE FROM goals")
    write_with_retry(write)
