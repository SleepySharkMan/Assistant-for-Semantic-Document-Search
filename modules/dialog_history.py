import sqlite3
import logging
from typing import List, Dict
from pathlib import Path

from config_models import DialogHistoryConfig

logger = logging.getLogger(__name__)

class DialogHistory:
    def __init__(self, config: DialogHistoryConfig):
        Path(config.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.conn = sqlite3.connect(config.db_path, check_same_thread=False)
        self._create_table()
        logger.info("DialogHistory подключена: %s", config.db_path)

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
        logger.debug("Сохранён диалог %s: %s → %s", user_id, user_text, assistant_text)

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
        logger.debug("Загрузка %d записей для %s", limit, user_id)
        return [
            {"timestamp": r[0], "user": r[1], "assistant": r[2]}
            for r in rows
        ]

    def clear_user_history(self, user_id: str) -> None:
        self.conn.execute("DELETE FROM dialogs WHERE user_id = ?", (user_id,))
        self.conn.commit()
        logger.info("История очищена для %s", user_id)

    def close(self):
        self.conn.close()

    def update_config(self, new_config: DialogHistoryConfig) -> None:
        if new_config.db_path != self.config.db_path:
            self.conn.close()
            self.__init__(new_config)
        else:
            self.config = new_config

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()
