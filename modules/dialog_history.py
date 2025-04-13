import sqlite3
from typing import List, Dict
from pathlib import Path


class DialogHistory:
    def __init__(self, db_path: str = "dialog_history.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dialogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save(self, user_id: str, user_text: str, assistant_text: str) -> None:
        self.conn.execute(
            "INSERT INTO dialogs (user_id, user_text, assistant_text) VALUES (?, ?, ?)",
            (user_id.strip(), user_text.strip(), assistant_text.strip())
        )
        self.conn.commit()

    def fetch_latest(self, user_id: str, limit: int = 30) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT timestamp, user_text, assistant_text 
            FROM dialogs 
            WHERE user_id = ? 
            ORDER BY id DESC 
            LIMIT ?
            """,
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [
            {"timestamp": r[0], "user": r[1], "assistant": r[2]}
            for r in rows
        ]

    def clear_user_history(self, user_id: str) -> None:
        self.conn.execute("DELETE FROM dialogs WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()
