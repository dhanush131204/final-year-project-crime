import sqlite3
from pathlib import Path
import datetime

DB_PATH = Path(__file__).resolve().parent / "database" / "records.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check current data
cur.execute("SELECT * FROM criminals")
current_data = cur.fetchall()
print("Current data:", current_data)

# Clear and reset with ID 1
cur.execute("DELETE FROM criminals")
cur.execute("DELETE FROM keys")
cur.execute("DELETE FROM logs")

# Reset auto-increment
cur.execute("DELETE FROM sqlite_sequence WHERE name='criminals'")

# Add Ramesh Kumar with ID 1
cur.execute(
    "INSERT INTO criminals(id, name, crime_type, photo_path, tile_dir, honey_path, created_at) VALUES (?,?,?,?,?,?,?)",
    (
        1,
        "Ramesh Kumar",
        "Burglary & Possession of Illegal Firearms",
        "static/uploads/sample_photo.jpg",
        "static/tiles/sample_tiles",
        "static/honey_data/sample_honey.png",
        datetime.datetime.utcnow().isoformat(),
    ),
)

conn.commit()
conn.close()
print("Ramesh Kumar set with ID 1 and crime type 'Theft'!")