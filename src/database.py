# src/database.py
import sqlite3
from pathlib import Path

# Database file will be at the project root
DB_FILE = Path(__file__).resolve().parent.parent / 'backtests.db'

def init_db():
    """Initializes the database and creates the tasks table if it doesn't exist."""
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        # Create table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS backtest_tasks (
                task_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                result_json TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            )
        ''')
        con.commit()
        con.close()
        print(f"Database initialized at {DB_FILE}")
    except Exception as e:
        print(f"Error initializing database: {e}")

if __name__ == '__main__':
    # This allows you to create the DB by running `python src/database.py`
    init_db()