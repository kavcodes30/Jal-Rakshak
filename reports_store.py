
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


def initialize_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS submitted_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT NOT NULL,
                station_name TEXT,
                state TEXT,
                water_body TEXT,
                reading_date TEXT,
                latitude REAL,
                longitude REAL,
                risk_level TEXT NOT NULL,
                high_risk_alert INTEGER NOT NULL,
                prediction_mode TEXT,
                probabilities TEXT,
                reading_data TEXT,
                prediction_data TEXT
            )
        """)


def save_report(reading, result):
    initialize_database()

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO submitted_reports (
                submitted_at,
                station_name,
                state,
                water_body,
                reading_date,
                latitude,
                longitude,
                risk_level,
                high_risk_alert,
                prediction_mode,
                probabilities,
                reading_data,
                prediction_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            reading.get("station_name"),
            reading.get("state"),
            reading.get("water_body"),
            reading.get("timestamp"),
            reading.get("lat"),
            reading.get("lon"),
            result["risk_level"],
            int(bool(result["alert"])),
            result.get("mode"),
            json.dumps(result.get("probabilities", {})),
            json.dumps(reading),
            json.dumps(result)
        ))

        return cursor.lastrowid


def get_submitted_reports():
    initialize_database()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT *
            FROM submitted_reports
            ORDER BY submitted_at DESC
        """).fetchall() 

    return [dict(row) for row in rows]
