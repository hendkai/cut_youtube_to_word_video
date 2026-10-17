"""SQLite-Index über die Wort-Videos."""
import os
import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY,
    word TEXT NOT NULL,
    file_name TEXT NOT NULL,
    duration_ms INTEGER,
    start_time REAL,
    end_time REAL,
    rated INTEGER NOT NULL DEFAULT -1,
    source_title TEXT,
    UNIQUE(word, file_name)
);
CREATE INDEX IF NOT EXISTS idx_videos_word ON videos(word);
CREATE INDEX IF NOT EXISTS idx_videos_rated ON videos(rated);
"""


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def insert_clip(
    word: str,
    file_name: str,
    duration_ms: int,
    start_time: float,
    end_time: float,
    source_title: str = "",
    db_path: str | None = None,
) -> int:
    with connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO videos
                (word, file_name, duration_ms, start_time, end_time, rated, source_title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (word, file_name, int(duration_ms), start_time, end_time,
             config.RATED_UNRATED, source_title),
        )
        return int(cur.lastrowid or 0)


def clip_path(word: str, file_name: str) -> str:
    return os.path.join(config.WORDS_DIR, word, file_name)


def unrated_clips(db_path: str | None = None) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM videos WHERE rated = ? ORDER BY word, id",
            (config.RATED_UNRATED,),
        ).fetchall()


def set_rating(clip_id: int, rating: int, db_path: str | None = None) -> None:
    if rating not in (config.RATED_GOOD, config.RATED_BAD):
        raise ValueError(f"Ungültige Bewertung: {rating}")
    with connect(db_path) as conn:
        conn.execute("UPDATE videos SET rated = ? WHERE id = ?", (rating, clip_id))


def best_clip_for_word(word: str, db_path: str | None = None) -> sqlite3.Row | None:
    """Bestes Clip für ein Wort: bevorzugt 'gut' bewertet, dann möglichst ~0,6 s."""
    with connect(db_path) as conn:
        return conn.execute(
            """
            SELECT * FROM videos
            WHERE word = ? AND rated != ?
            ORDER BY CASE rated WHEN ? THEN 0 ELSE 1 END,
                     ABS(duration_ms - 600),
                     id
            LIMIT 1
            """,
            (word, config.RATED_BAD, config.RATED_GOOD),
        ).fetchone()


def stats(db_path: str | None = None) -> dict:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(rated = ?) AS good,
                   SUM(rated = ?) AS bad,
                   SUM(rated = ?) AS unrated,
                   COUNT(DISTINCT word) AS words
            FROM videos
            """,
            (config.RATED_GOOD, config.RATED_BAD, config.RATED_UNRATED),
        ).fetchone()
    return {
        "total": row["total"] or 0,
        "good": row["good"] or 0,
        "bad": row["bad"] or 0,
        "unrated": row["unrated"] or 0,
        "words": row["words"] or 0,
    }
