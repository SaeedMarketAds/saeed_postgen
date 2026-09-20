# ================================================================
# SAEED POSTGEN 4.6
# DATABASE ENGINE
# FILE: core/database.py
# ================================================================

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


# ----------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "postgen.db"


# ----------------------------------------------------------------
# CONNECTION
# ----------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    إنشاء اتصال بقاعدة بيانات Saeed PostGen.
    """

    connection = sqlite3.connect(
        DB_PATH,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


# ----------------------------------------------------------------
# DATABASE INITIALIZATION
# ----------------------------------------------------------------

def init_database() -> None:
    """
    إنشاء جميع الجداول الأساسية للمنصة.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # ============================================================
    # USERS
    # ============================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'merchant',
            full_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ============================================================
    # STORES
    # ============================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,

            page_name TEXT DEFAULT '',
            slug TEXT DEFAULT '',

            logo_path TEXT DEFAULT '',
            cover_path TEXT DEFAULT '',

            primary_color TEXT DEFAULT '#D4AF37',
            secondary_color TEXT DEFAULT '#0B0F19',

            phone TEXT DEFAULT '',
            description TEXT DEFAULT '',
            business_type TEXT DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
        )
        """
    )

    # ============================================================
    # PRODUCTS
    # ============================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,

            name TEXT NOT NULL,
            description TEXT DEFAULT '',

            price TEXT DEFAULT '',
            currency TEXT DEFAULT '',

            image_path TEXT DEFAULT '',

            specifications TEXT DEFAULT '',

            is_active INTEGER NOT NULL DEFAULT 1,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id),

            FOREIGN KEY (store_id)
                REFERENCES stores(id)
        )
        """
    )

    # ============================================================
    # CONTENT
    # ============================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,

            content_type TEXT NOT NULL,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',

            file_path TEXT DEFAULT '',

            status TEXT NOT NULL DEFAULT 'REVIEW',

            guard_reason TEXT DEFAULT '',

            reviewed_at TEXT DEFAULT '',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id),

            FOREIGN KEY (store_id)
                REFERENCES stores(id)
        )
        """
    )

    # ============================================================
    # CAMPAIGNS
    # ============================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,
            store_id INTEGER NOT NULL,

            name TEXT NOT NULL,
            objective TEXT DEFAULT '',

            platform TEXT DEFAULT '',

            budget TEXT DEFAULT '',
            currency TEXT DEFAULT '',

            start_date TEXT DEFAULT '',
            end_date TEXT DEFAULT '',

            status TEXT NOT NULL DEFAULT 'DRAFT',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id),

            FOREIGN KEY (store_id)
                REFERENCES stores(id)
        )
        """
    )

    # ============================================================
    # REPORTS
    # ============================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            content_id INTEGER NOT NULL,
            reporter_user_id INTEGER DEFAULT 0,

            reason TEXT DEFAULT '',
            details TEXT DEFAULT '',

            status TEXT NOT NULL DEFAULT 'OPEN',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at TEXT DEFAULT '',

            FOREIGN KEY (content_id)
                REFERENCES content(id)
        )
        """
    )

    # ============================================================
    # INDEXES
    # ============================================================

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_users_role
        ON users(role)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_stores_user
        ON stores(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_products_user
        ON products(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_content_user
        ON content(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_content_status
        ON content(status)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_campaigns_user
        ON campaigns(user_id)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_reports_status
        ON reports(status)
        """
    )

    connection.commit()
    connection.close()


# ----------------------------------------------------------------
# GENERIC HELPERS
# ----------------------------------------------------------------

def execute(
    query: str,
    parameters: tuple[Any, ...] = (),
) -> int:
    """
    تنفيذ INSERT / UPDATE / DELETE.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(query, parameters)

        connection.commit()

        return cursor.lastrowid or 0

    finally:
        connection.close()


def fetch_one(
    query: str,
    parameters: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """
    جلب سجل واحد.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(query, parameters)

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        connection.close()


def fetch_all(
    query: str,
    parameters: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """
    جلب مجموعة سجلات.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(query, parameters)

        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ----------------------------------------------------------------
# STARTUP
# ----------------------------------------------------------------

init_database()
