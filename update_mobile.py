import sqlite3
from pathlib import Path
import datetime

DB_PATH = Path(__file__).resolve().parent / "database" / "records.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Add mobile column if it doesn't exist
try:
    cur.execute("ALTER TABLE criminals ADD COLUMN mobile TEXT")
    print("Added mobile column")
except sqlite3.OperationalError:
    print("Mobile column already exists")

# Update Ramesh Kumar with mobile number
cur.execute(
    "UPDATE criminals SET mobile = ? WHERE name = ?",
    ("9876543210", "Ramesh Kumar")
)

# Check the updated data
cur.execute("SELECT * FROM criminals")
data = cur.fetchall()
print("Updated data:", data)

conn.commit()
conn.close()
print("Mobile number added to Ramesh Kumar!")