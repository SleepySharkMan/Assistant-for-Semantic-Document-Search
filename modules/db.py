import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from .models import Base

class DBManager:
    def __init__(self, db_config, echo: bool = False):
        database_url = db_config.url

        # Если SQLite — гарантируем наличие каталога
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
            echo=echo
        )
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def session_scope(self):
        db = self.Session()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()