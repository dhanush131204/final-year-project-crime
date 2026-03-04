import sqlite3
from werkzeug.security import generate_password_hash
from pathlib import Path
import datetime

DB_PATH = Path(__file__).resolve().parent / "database" / "records.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Clear existing data
cur.execute("DELETE FROM criminals")
cur.execute("DELETE FROM keys")
cur.execute("DELETE FROM logs")

# Add only Ramesh Kumar
cur.execute(
    "INSERT INTO criminals(name, crime_type, photo_path, tile_dir, honey_path, created_at) VALUES (?,?,?,?,?,?)",
    (
        "Ramesh Kumar",
        "Theft",
        "static/uploads/sample_photo.jpg",
        "static/tiles/sample_tiles",
        "static/honey_data/sample_honey.png",
        datetime.datetime.utcnow().isoformat(),
    ),
)

conn.commit()
conn.close()
print("Database cleared and Ramesh Kumar added!")