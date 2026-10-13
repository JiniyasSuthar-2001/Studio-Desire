import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "studio_desire.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Update test fixture records to be unpublished / deleted
cursor.execute("UPDATE projects SET is_published = 0 WHERE title LIKE '%Public Project with Mixed Media%' OR title LIKE '%Secret Unpublished Villa%' OR title LIKE '%Shah Sky Penthouse%' OR slug = 'test-task-villa'")
conn.commit()

cursor.execute("SELECT id, title, slug, category, project_type, is_published, featured FROM projects WHERE is_published = 1 ORDER BY id ASC")
rows = cursor.fetchall()
print(f"Total published portfolio projects: {len(rows)}")
for r in rows:
    print(r)

conn.close()
