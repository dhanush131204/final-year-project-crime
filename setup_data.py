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
    """INSERT INTO criminals(
        name, mobile, crime_type, photo_path, tile_dir, honey_path, 
        age_gender, address, ps1, fir1, ps2, fir2, ps3, 
        arrest_date, case1, ps4_section, case2, id_marks, 
        honey_name, honey_crime_type, created_at
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (
        "Ramesh Kumar", "", "Theft", "static/records/primary_vault/sample_photo.jpg",
        "static/tiles/sample_tiles", "static/records/decoy_vault/sample_honey.png",
        "40 / M", "Bangalore, India", "Central PS", "101/24", "North PS", "202/24", "East PS",
        "20/03/2024", "CR/2024/01", "IPC 379", "CR/2024/02", "None", 
        "Suresh Raina", "Official Record", datetime.datetime.utcnow().isoformat(),
    ),
)

conn.commit()
conn.close()
print("Database cleared and Ramesh Kumar added!")