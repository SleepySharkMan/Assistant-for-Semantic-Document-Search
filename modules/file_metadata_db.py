import sqlite3
import logging

from pathlib import Path
from typing import Optional, Dict, List

from config_models import FileMetadataDBConfig

logger = logging.getLogger(__name__)

class FileMetadataDB:
    def __init__(self, config: FileMetadataDBConfig):
        self.config = config
        self.db_path = config.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()
        logger.info("FileMetadataDB подключена: %s", self.db_path)

    def update_config(self, new_config: FileMetadataDBConfig) -> None:
        if new_config.db_path != self.config.db_path:
            if hasattr(self, "conn"):
                self.conn.close()
            self.config = new_config
            self.db_path = new_config.db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(self.db_path)
            self._create_tables()
        else:
            self.config = new_config

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                size INTEGER NOT NULL,
                hash TEXT(64) UNIQUE NOT NULL,
                processed INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS images (
                file_id INTEGER PRIMARY KEY,
                width INTEGER,
                height INTEGER,
                thumbnail BLOB,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def add_file(self, path: str, file_type: str, size: int, file_hash: str) -> Optional[int]:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO files 
                (path, file_type, size, hash) 
                VALUES (?, ?, ?, ?)""",
                (path, file_type, size, file_hash)
            )
            self.conn.commit()

            if cursor.lastrowid == 0:
                existing = self.get_file_by_hash(file_hash)
                if existing:
                    logger.info("Файл %s уже добавлен ранее.", path)
                    return None
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error("Ошибка добавления файла: %s", e, exc_info=True)
            return None

    def mark_file_as_processed(self, file_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE files SET processed = 1 WHERE id = ?",
            (file_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def is_file_processed(self, file_path: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT processed FROM files WHERE path = ?",
            (file_path,)
        )
        result = cursor.fetchone()
        return result[0] == 1 if result else False

    def get_file_by_hash(self, file_hash: str) -> Optional[Dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, path, file_type, size, hash, processed, created_at 
            FROM files WHERE hash = ?""",
            (file_hash,)
        )
        result = cursor.fetchone()
        if result and len(result) == 7:
            return {
                "id": result[0],
                "path": result[1],
                "type": result[2],
                "size": result[3],
                "hash": result[4],
                "processed": bool(result[5]),
                "created_at": result[6]
            }
        return None

    def add_image_metadata(self, file_id: int, width: int, height: int, thumbnail: bytes) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO images 
                (file_id, width, height, thumbnail) 
                VALUES (?, ?, ?, ?)""",
                (file_id, width, height, thumbnail)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning("Файл с ID %s не существует", file_id)
            return False

    def get_all_files(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files")
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_files_by_extension(self, extension: Optional[str] = None) -> List[str]:
        cursor = self.conn.cursor()
        if extension:
            if not extension.startswith('.'):
                extension = '.' + extension
            extension = extension.lower()
            cursor.execute(
                "SELECT path FROM files WHERE LOWER(path) LIKE ?",
                (f"%{extension}",)
            )
        else:
            cursor.execute("SELECT path FROM files")
        return [row[0] for row in cursor.fetchall()]

    def is_supported_format(self, file_path: str, allowed_extensions: List[str]) -> bool:
        from pathlib import Path
        ext = Path(file_path).suffix.lower()
        return ext in allowed_extensions

    def delete_file(self, file_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def _row_to_dict(self, row) -> Dict:
        return {
            "id": row[0],
            "path": row[1],
            "type": row[2],
            "size": row[3],
            "hash": row[4],
            "processed": bool(row[5]),
            "created_at": row[6]
        }

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()
