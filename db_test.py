import sqlite3
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler("check_db.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DB_PATH = "D:\\Assistant-for-Semantic-Document-Search\\data\\database.db"

def check_database():
    """Проверяет базу данных файлов на дубликаты и наличие файлов."""
    if not Path(DB_PATH).exists():
        logger.error("База данных не найдена: %s", DB_PATH)
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. Все записи
        logger.info("=== Все записи в таблице files ===")
        cursor.execute("""
            SELECT id, path, file_type, size, hash, created_at, splitter_method
            FROM files
            ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        if not rows:
            logger.info("Таблица files пуста")
        else:
            for row in rows:
                logger.info("ID: %s, Path: %s, Type: %s, Size: %s, Hash: %s, Created: %s, Splitter: %s",
                            *row)

        # 2. Дубликаты по path
        logger.info("\n=== Дубликаты по path ===")
        cursor.execute("""
            SELECT path, COUNT(*) as count
            FROM files
            GROUP BY path
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if not duplicates:
            logger.info("Дубликатов по path не найдено")
        else:
            for path, count in duplicates:
                logger.warning("Дубликат: Path: %s, Количество: %s", path, count)

        # 3. Дубликаты по hash
        logger.info("\n=== Дубликаты по hash ===")
        cursor.execute("""
            SELECT hash, COUNT(*) as count
            FROM files
            GROUP BY hash
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if not duplicates:
            logger.info("Дубликатов по hash не найдено")
        else:
            for hash_val, count in duplicates:
                logger.warning("Дубликат: Hash: %s, Количество: %s", hash_val, count)

        # 4. Поиск Ефим Честняков.pdf
        logger.info("\n=== Поиск Ефим Честняков.pdf ===")
        cursor.execute("""
            SELECT id, path, file_type, size, hash, created_at
            FROM files
            WHERE path LIKE '%Ефим Честняков.pdf'
        """)
        rows = cursor.fetchall()
        if not rows:
            logger.info("Файл Ефим Честняков.pdf не найден")
        else:
            for row in rows:
                logger.info("ID: %s, Path: %s, Type: %s, Size: %s, Hash: %s, Created: %s", *row)

        # 5. Поиск .docx файлов
        logger.info("\n=== Поиск .docx файлов ===")
        cursor.execute("""
            SELECT id, path, file_type, size, hash, created_at
            FROM files
            WHERE path LIKE '%.docx'
        """)
        rows = cursor.fetchall()
        if not rows:
            logger.info("Файлы .docx не найдены")
        else:
            for row in rows:
                logger.info("ID: %s, Path: %s, Type: %s, Size: %s, Hash: %s, Created: %s", *row)

        # 6. Записи без хэша
        logger.info("\n=== Записи без хэша ===")
        cursor.execute("""
            SELECT id, path, file_type, size, hash
            FROM files
            WHERE hash = '' OR hash IS NULL
        """)
        rows = cursor.fetchall()
        if not rows:
            logger.info("Записей без хэша не найдено")
        else:
            for row in rows:
                logger.warning("Без хэша: ID: %s, Path: %s, Type: %s, Size: %s, Hash: %s", *row)

        conn.close()
    except sqlite3.Error as e:
        logger.error("Ошибка при работе с базой данных: %s", e)

if __name__ == "__main__":
    check_database()