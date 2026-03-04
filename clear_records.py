import sqlite3
from pathlib import Path

# Database path
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "records.db"

def clear_criminal_records():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Delete all criminal records
        cur.execute("DELETE FROM criminals")
        
        # Delete all keys
        cur.execute("DELETE FROM keys")
        
        # Delete all logs
        cur.execute("DELETE FROM logs")
        
        # Reset auto-increment counters
        cur.execute("DELETE FROM sqlite_sequence WHERE name='criminals'")
        cur.execute("DELETE FROM sqlite_sequence WHERE name='keys'")
        cur.execute("DELETE FROM sqlite_sequence WHERE name='logs'")
        
        conn.commit()
        conn.close()
        
        print("All criminal records, keys, and logs have been cleared successfully!")
        print("Database is now clean and ready for new records.")
        
    except Exception as e:
        print(f"Error clearing records: {str(e)}")

if __name__ == "__main__":
    clear_criminal_records()