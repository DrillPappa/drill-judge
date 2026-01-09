import os
import sqlite3
import time
from typing import Optional, Dict, Any

DB_PATH = os.getenv("JOB_DB_PATH", "/tmp/drill_jobs.sqlite")

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = _conn()
    conn.execute("""
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        result_json TEXT,
        error TEXT,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL
      )
    """)
    conn.commit()
    conn.close()

def create_job(job_id: str):
    now = int(time.time())
    conn = _conn()
    conn.execute(
        "INSERT INTO jobs (id, status, result_json, error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (job_id, "queued", None, None, now, now)
    )
    conn.commit()
    conn.close()

def set_status(job_id: str, status: str, result_json: Optional[str] = None, error: Optional[str] = None):
    now = int(time.time())
    conn = _conn()
    conn.execute(
        "UPDATE jobs SET status=?, result_json=?, error=?, updated_at=? WHERE id=?",
        (status, result_json, error, now, job_id)
    )
    conn.commit()
    conn.close()

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    conn = _conn()
    cur = conn.execute("SELECT id, status, result_json, error, created_at, updated_at FROM jobs WHERE id=?", (job_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "status": row[1],
        "result_json": row[2],
        "error": row[3],
        "created_at": row[4],
        "updated_at": row[5],
    }
