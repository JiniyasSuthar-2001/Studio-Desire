#!/usr/bin/env python3
"""
Studio Desire — Database Backup & Disaster Recovery Utility
Performs online, consistent SQLite backups using sqlite3's native online backup API.
Safely backs up active databases without locking or corruption.
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BACKEND_DIR / "studio_desire.db"
BACKUPS_DIR = BACKEND_DIR / "backups"


def create_backup(custom_dest: str = None) -> Path:
    if not DB_PATH.exists():
        print(f"[ERROR] Database file does not exist at {DB_PATH}")
        sys.exit(1)

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = Path(custom_dest) if custom_dest else BACKUPS_DIR / f"studio_desire_backup_{timestamp}.db"

    print(f"[INFO] Initializing online backup from: {DB_PATH}")
    print(f"[INFO] Destination backup path: {target_path}")

    # Use SQLite's online backup API for complete transaction safety
    src_conn = sqlite3.connect(str(DB_PATH))
    dst_conn = sqlite3.connect(str(target_path))

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
        print(f"[SUCCESS] Database backup created successfully: {target_path} ({target_path.stat().st_size} bytes)")
        return target_path
    finally:
        src_conn.close()
        dst_conn.close()


def restore_backup(backup_file: str) -> None:
    backup_path = Path(backup_file)
    if not backup_path.exists():
        print(f"[ERROR] Backup file not found: {backup_path}")
        sys.exit(1)

    print(f"[WARNING] Restoring database from backup: {backup_path} -> {DB_PATH}")
    src_conn = sqlite3.connect(str(backup_path))
    dst_conn = sqlite3.connect(str(DB_PATH))

    try:
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
        print(f"[SUCCESS] Database successfully restored from {backup_path}")
    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        if len(sys.argv) < 3:
            print("Usage: python backup_db.py --restore <path_to_backup.db>")
            sys.exit(1)
        restore_backup(sys.argv[2])
    else:
        create_backup()
