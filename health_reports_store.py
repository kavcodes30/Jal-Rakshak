
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "submitted_reports.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_health_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS community_health_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT NOT NULL,
                report_date TEXT NOT NULL,
                state TEXT NOT NULL,
                district TEXT NOT NULL,
                village TEXT,
                people_affected INTEGER NOT NULL,
                symptoms TEXT NOT NULL,
                water_source TEXT,
                additional_notes TEXT
            )
        """)


def save_health_report(report):
    initialize_health_database()

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO community_health_reports (
                submitted_at,
                report_date,
                state,
                district,
                village,
                people_affected,
                symptoms,
                water_source,
                additional_notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            str(report["report_date"]),
            report["state"],
            report["district"],
            report.get("village", ""),
            int(report["people_affected"]),
            json.dumps(report["symptoms"]),
            report.get("water_source", ""),
            report.get("additional_notes", "")
        ))

        return cursor.lastrowid


def get_health_reports():
    initialize_health_database()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM community_health_reports
            ORDER BY submitted_at DESC
        """).fetchall()

    reports = [dict(row) for row in rows]

    for report in reports:
        report["symptoms"] = json.loads(report["symptoms"])

    return reports
