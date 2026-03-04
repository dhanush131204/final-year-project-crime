import sqlite3
from werkzeug.security import generate_password_hash
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "database" / "records.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Update admin user with proper password hash
cur.execute(
    "UPDATE users SET password_hash = ? WHERE role = 'admin' AND username = 'admin'",
    (generate_password_hash("Admin123"),)
)

conn.commit()
conn.close()
print("Admin password fixed!")