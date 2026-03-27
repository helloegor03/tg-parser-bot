# ============================================================
#  db.py — SQLite: состояния, кэш, избранное, подписки
# ============================================================

import sqlite3
import json
import time
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создаём таблицы при первом запуске."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id   INTEGER PRIMARY KEY,
                state     TEXT    NOT NULL DEFAULT '',
                data      TEXT    NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS cache (
                key        TEXT    PRIMARY KEY,
                payload    TEXT    NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                vacancy_id TEXT    NOT NULL,
                title      TEXT,
                company    TEXT,
                url        TEXT,
                salary     TEXT,
                saved_at   INTEGER NOT NULL,
                UNIQUE(user_id, vacancy_id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                keyword         TEXT    NOT NULL,
                city_id         INTEGER,
                city_name       TEXT,
                experience      TEXT,
                salary_from     INTEGER,
                employment      TEXT,
                last_check      INTEGER DEFAULT 0,
                known_ids       TEXT    DEFAULT '[]'
            );
        """)


# ─── Состояния пользователей ────────────────────────────────

def get_state(user_id: int) -> tuple[str, dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT state, data FROM user_states WHERE user_id = ?", (user_id,)
        ).fetchone()
    if row:
        return row["state"], json.loads(row["data"])
    return "", {}


def set_state(user_id: int, state: str, data: dict = None):
    if data is None:
        data = {}
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_states (user_id, state, data)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state=excluded.state, data=excluded.data
        """, (user_id, state, json.dumps(data, ensure_ascii=False)))


def clear_state(user_id: int):
    set_state(user_id, "", {})


# ─── Кэш ────────────────────────────────────────────────────

def cache_get(key: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
    if row and row["expires_at"] > time.time():
        return json.loads(row["payload"])
    return None


def cache_set(key: str, value, ttl: int):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO cache (key, payload, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, expires_at=excluded.expires_at
        """, (key, json.dumps(value, ensure_ascii=False), int(time.time()) + ttl))


def cache_cleanup():
    """Чистим устаревший кэш."""
    with get_conn() as conn:
        conn.execute("DELETE FROM cache WHERE expires_at < ?", (int(time.time()),))


# ─── Избранное ──────────────────────────────────────────────

def fav_add(user_id: int, vacancy: dict) -> bool:
    """True если добавлено, False если уже есть."""
    try:
        with get_conn() as conn:
            conn.execute("""
                INSERT INTO favorites (user_id, vacancy_id, title, company, url, salary, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                vacancy["id"],
                vacancy.get("title"),
                vacancy.get("company"),
                vacancy.get("url"),
                vacancy.get("salary"),
                int(time.time()),
            ))
        return True
    except sqlite3.IntegrityError:
        return False


def fav_remove(user_id: int, vacancy_id: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND vacancy_id = ?",
            (user_id, vacancy_id),
        )


def fav_list(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM favorites WHERE user_id = ? ORDER BY saved_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def fav_exists(user_id: int, vacancy_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND vacancy_id = ?",
            (user_id, vacancy_id),
        ).fetchone()
    return row is not None


# ─── Подписки ───────────────────────────────────────────────

def sub_add(user_id: int, filters: dict) -> int:
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO subscriptions
                (user_id, keyword, city_id, city_name, experience, salary_from, employment)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            filters["keyword"],
            filters.get("city_id"),
            filters.get("city_name"),
            filters.get("experience"),
            filters.get("salary_from"),
            filters.get("employment"),
        ))
    return cur.lastrowid


def sub_list(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def sub_delete(sub_id: int, user_id: int):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user_id)
        )


def sub_all() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM subscriptions").fetchall()
    return [dict(r) for r in rows]


def sub_update_known(sub_id: int, known_ids: list, last_check: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE subscriptions SET known_ids = ?, last_check = ? WHERE id = ?",
            (json.dumps(known_ids), last_check, sub_id),
        )
