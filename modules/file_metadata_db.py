import sqlite3

from typing import Optional, Dict, List
from config_models import FileMetadataDBConfig


class FileMetadataDB:
    def __init__(self, config: FileMetadataDBConfig):
        self.config = config
        self.db_path = config.db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def update_config(self, new_config: FileMetadataDBConfig):
        self.conn.close()
        self.__init__(new_config)

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
                    print(f"Файл {path} уже добавлен ранее.")
                    return None
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Ошибка добавления файла: {str(e)}")
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
            print(f"Файл с ID {file_id} не существует")
            return False

    def get_all_files(self) -> List[Dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM files")
        return [self._row_to_dict(row) for row in cursor.fetchall()]

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

    def delete_file(self, file_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def __del__(self):
        self.conn.close()
