import os
import sqlite3
from datetime import datetime
from typing import Iterable, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "app.db")


def _ensure_dir() -> None:
    os.makedirs(DB_DIR, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(super_admin_email: str) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                email TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS featured (
                project_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )
        if super_admin_email:
            conn.execute(
                "INSERT OR IGNORE INTO admins (email, created_at) VALUES (?, ?)",
                (super_admin_email.lower(), datetime.utcnow().isoformat()),
            )


def list_admins() -> List[str]:
    conn = _connect()
    rows = conn.execute("SELECT email FROM admins ORDER BY email").fetchall()
    return [row["email"] for row in rows]


def add_admin(email: str) -> None:
    if not email:
        return
    conn = _connect()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO admins (email, created_at) VALUES (?, ?)",
            (email.lower(), datetime.utcnow().isoformat()),
        )


def remove_admin(email: str) -> None:
    if not email:
        return
    conn = _connect()
    with conn:
        conn.execute("DELETE FROM admins WHERE email = ?", (email.lower(),))


def is_admin(email: str) -> bool:
    if not email:
        return False
    conn = _connect()
    row = conn.execute(
        "SELECT 1 FROM admins WHERE email = ?",
        (email.lower(),),
    ).fetchone()
    return row is not None


def list_featured_ids() -> List[int]:
    conn = _connect()
    rows = conn.execute(
        "SELECT project_id FROM featured ORDER BY created_at DESC"
    ).fetchall()
    return [int(row["project_id"]) for row in rows]


def add_featured(ids: Iterable[int]) -> None:
    ids = [int(item) for item in ids if str(item).isdigit()]
    if not ids:
        return
    conn = _connect()
    with conn:
        for project_id in ids:
            conn.execute(
                "INSERT OR IGNORE INTO featured (project_id, created_at) VALUES (?, ?)",
                (project_id, datetime.utcnow().isoformat()),
            )


def remove_featured(project_id: int) -> None:
    conn = _connect()
    with conn:
        conn.execute("DELETE FROM featured WHERE project_id = ?", (project_id,))
