import os
import sys
import sqlite3
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
db_path = backend_dir / "studio_desire.db"
uploads_root = (backend_dir.parent / "frontend" / "public" / "uploads").resolve()

print(f"Database: {db_path} (exists: {db_path.exists()})")
print(f"Uploads Root: {uploads_root} (exists: {uploads_root.exists()})")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

def check_table(table, id_col, cols):
    print(f"\n--- Checking Table: {table} ---")
    missing_count = 0
    total_count = 0
    for col in cols:
        cur.execute(f"SELECT {id_col}, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''")
        rows = cur.fetchall()
        for rid, val in rows:
            total_count += 1
            clean = val.strip()
            if clean.startswith("/uploads/"):
                rel = clean[len("/uploads/"):]
                fpath = uploads_root / rel
                if not fpath.exists():
                    missing_count += 1
                    print(f"  [MISSING] {table} #{rid} {col}: '{clean}' -> {fpath}")
            elif clean.startswith("http://") or clean.startswith("https://") or clean.startswith("data:"):
                pass
            else:
                print(f"  [NON-STANDARD URL] {table} #{rid} {col}: '{clean}'")
    print(f"Table {table}: checked {total_count} URLs, found {missing_count} missing files.")

check_table("projects", "id", ["cover_image"])
check_table("project_media", "id", ["url", "thumbnail_url"])
check_table("visualization_spaces", "id", ["cover_image"])
check_table("visualization_media", "id", ["url"])
check_table("blueprint_drawings", "id", ["file_url", "thumbnail_url"])

conn.close()
