import logging
from .models import Dialog

logger = logging.getLogger(__name__)

class DialogHistory:
    def __init__(self, session_factory):
        """
        session_factory — функция, возвращающая контекстный менеджер SQLAlchemy-сессии.
        Обычно это DBManager.session_scope
        """
        self.session_factory = session_factory

    def save(self, user_id: str, user_text: str, assistant_text: str) -> None:
        with self.session_factory() as session:
            dialog = Dialog(
                user_id=user_id.strip(),
                user_text=user_text.strip(),
                assistant_text=assistant_text.strip()
            )
            session.add(dialog)
            logger.debug("Сохранён диалог: %s -> %s", user_text.strip(), assistant_text.strip())

    def fetch_latest(self, user_id: str, limit: int = 30) -> list[dict]:
        with self.session_factory() as session:
            rows = (session.query(Dialog)
                    .filter(Dialog.user_id == user_id)
                    .order_by(Dialog.id.desc())
                    .limit(limit)
                    .all())
            logger.debug("Получено %d записей диалога для пользователя %s", len(rows), user_id)
            return [
                {"timestamp": r.timestamp, "user": r.user_text, "assistant": r.assistant_text}
                for r in reversed(rows)
            ]

    def clear_user_history(self, user_id: str) -> None:
        with self.session_factory() as session:
            deleted = session.query(Dialog).filter(Dialog.user_id == user_id).delete()
            logger.info("Удалено %d записей истории для пользователя %s", deleted, user_id)