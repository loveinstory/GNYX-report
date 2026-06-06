from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import settings


def connect() -> sqlite3.Connection:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS credentials (
              credential_id TEXT PRIMARY KEY,
              provider TEXT NOT NULL,
              label TEXT NOT NULL,
              encrypted_value TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
              user_id TEXT PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL,
              is_active INTEGER NOT NULL DEFAULT 1,
              last_login_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
              session_id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              expires_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              revoked_at TEXT,
              FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
              job_id TEXT PRIMARY KEY,
              job_type TEXT NOT NULL,
              package_code TEXT NOT NULL,
              status TEXT NOT NULL,
              progress INTEGER NOT NULL,
              total INTEGER NOT NULL,
              succeeded INTEGER NOT NULL,
              failed INTEGER NOT NULL,
              message TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS imported_documents (
              document_id TEXT PRIMARY KEY,
              import_job_id TEXT NOT NULL,
              package_code TEXT NOT NULL,
              original_name TEXT NOT NULL,
              stored_name TEXT NOT NULL,
              stored_path TEXT NOT NULL,
              size INTEGER NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
              report_id TEXT PRIMARY KEY,
              case_id TEXT NOT NULL,
              package_code TEXT NOT NULL,
              status TEXT NOT NULL,
              template_version TEXT NOT NULL,
              rule_version TEXT NOT NULL,
              prompt_version TEXT NOT NULL,
              ai_model TEXT NOT NULL,
              snapshot_json TEXT NOT NULL,
              export_path TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ocr_parse_logs (
              log_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL,
              package_code TEXT NOT NULL,
              source_file TEXT NOT NULL,
              strategy_version TEXT NOT NULL,
              provider TEXT NOT NULL,
              status TEXT NOT NULL,
              confidence REAL NOT NULL,
              extracted_field_count INTEGER NOT NULL,
              result_json TEXT NOT NULL,
              notes TEXT NOT NULL,
              created_at TEXT NOT NULL,
              consumed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
              audit_id TEXT PRIMARY KEY,
              actor TEXT NOT NULL,
              action TEXT NOT NULL,
              target_type TEXT NOT NULL,
              target_id TEXT NOT NULL,
              detail_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(conn, "jobs", "completed_at", "TEXT")
        _ensure_column(conn, "ocr_parse_logs", "consumed_at", "TEXT")


def dict_from_row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def ensure_storage_dirs() -> None:
    for directory in (settings.storage_dir, settings.export_dir, settings.backup_dir, settings.cases_dir, settings.import_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    existing = {
        str(row["name"])
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
