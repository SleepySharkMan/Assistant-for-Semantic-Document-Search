import logging
from itertools import zip_longest
from flask import request, jsonify, send_file, render_template
from io import BytesIO

logger = logging.getLogger(__name__)

def register_routes(app, dialog_manager):
    @app.errorhandler(Exception)
    def handle_global_exception(error):
        logger.exception("Неперехваченное исключение: %s", error)
        return jsonify({"error": "Внутренняя ошибка сервера."}), 500

    @app.route("/api/message", methods=["POST"])
    def handle_text_message():
        data = request.get_json(silent=True) or {}
        user_id  = (data.get("user_id")  or "").strip()
        question = (data.get("message") or "").strip()

        # запрошенные флаги
        show_src  = bool(data.get("show_source_info"))
        show_frag = bool(data.get("show_text_fragments"))

        logger.info("HTTP %s %s user_id=%r", request.method, request.path, user_id)

        if not user_id:
            logger.warning("Нет user_id в запросе: %s", data)
            return jsonify({"error": "user_id обязателен"}), 400
        if not question:
            logger.warning("Пустой вопрос. user_id=%s", user_id)
            return jsonify({"error": "Вопрос не может быть пустым."}), 400

        # ── обращаемся к DialogManager ───────────────────────
        try:
            response = dialog_manager.answer_text(
                user_id=user_id,
                question=question,
                request_source_info=show_src,
                request_fragments=show_frag
            )
        except Exception as exc:
            logger.exception("Ошибка answer_text: %s", exc)
            return jsonify({"error": "Ошибка при обработке запроса."}), 500

        # ── собираем итог ───────────────────────────────────
        final: dict = {"answer": response.get("answer", "")}

        sources   = response.get("sources")     # None ⇒ источники не запрашивались
        fragments = response.get("fragments")   # None ⇒ фрагменты не запрашивались

        # Источники запрошены, но ни одного имени не нашли → «unknown»
        if sources is not None and not sources:
            sources = ["unknown"] * (len(fragments) if fragments else 1)

        # a) обе части есть → формируем results
        if sources is not None and fragments is not None:
            from itertools import zip_longest

            grouped: dict[str, list[str]] = {}
            for src, frag in zip_longest(sources, fragments, fillvalue=None):
                if src is None and frag is None:
                    continue
                key = src or "unknown"
                if frag:
                    grouped.setdefault(key, []).append(frag)

            if grouped:
                final["results"] = [
                    {"source": k, "fragments": v} for k, v in grouped.items()
                ]

        # b) только источники
        elif sources is not None:
            final["sources"] = list(dict.fromkeys(sources))

        # c) только фрагменты
        elif fragments is not None:
            final["fragments"] = fragments

        return jsonify(final), 200

    @app.route("/api/history", methods=["GET"])
    def get_history():
        user_id = (request.args.get("user_id") or "").strip()
        logger.info("HTTP %s %s user_id=%r", request.method, request.path, user_id)

        if not user_id:
            logger.warning("Некорректный запрос на получение истории: отсутствует user_id. Параметры=%s", request.args)
            return jsonify({"error": "user_id обязателен"}), 400

        try:
            entries = dialog_manager.history.fetch_latest(user_id=user_id, limit=30)
            messages = []
            for entry in reversed(entries):
                messages.append({"sender": "user", "text": entry["user"]})
                messages.append({"sender": "bot", "text": entry["assistant"]})
            return jsonify({"messages": messages}), 200
        except Exception as e:
            logger.exception("Ошибка при получении истории для пользователя %s: %s", user_id, e)
            return jsonify({"error": "Ошибка при получении истории."}), 500

    @app.route("/api/history", methods=["DELETE"])
    def delete_history():
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        logger.info("HTTP %s %s user_id=%r", request.method, request.path, user_id)

        if not user_id:
            logger.warning("Некорректный запрос на удаление истории: отсутствует user_id. Полезная нагрузка=%s", data)
            return jsonify({"error": "user_id обязателен"}), 400

        try:
            dialog_manager.history.clear_user_history(user_id)
            return jsonify({"success": True}), 200
        except Exception as e:
            logger.exception("Ошибка при удалении истории для пользователя %s: %s", user_id, e)
            return jsonify({"error": "Ошибка при удалении истории."}), 500

    @app.route("/api/speech-to-text", methods=["POST"])
    def handle_speech_to_text():
        user_id = (request.form.get("user_id") or request.args.get("user_id") or "").strip()
        logger.info("HTTP %s %s user_id=%r", request.method, request.path, user_id)

        if "audio" not in request.files:
            logger.warning("Некорректный запрос: аудиофайл не предоставлен. user_id=%s", user_id)
            return jsonify({"error": "Аудиофайл не предоставлен."}), 400

        audio_file = request.files["audio"]
        try:
            text = dialog_manager.answer_speech(audio_file.stream)
            if text is None:
                raise ValueError("Speech recognition вернул None")
            return jsonify({"text": text}), 200
        except Exception as e:
            logger.exception("Ошибка распознавания речи: %s", e)
            return jsonify({"error": "Ошибка распознавания речи."}), 500

    @app.route("/api/text-to-speech", methods=["POST"])
    def handle_text_to_speech():
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        text = (data.get("text") or "").strip()
        logger.info("HTTP %s %s user_id=%r text=%r", request.method, request.path, user_id, text)

        if not text:
            logger.warning("Некорректный запрос: пустой текст для синтеза речи. user_id=%s", user_id)
            return jsonify({"error": "Текст не может быть пустым."}), 400

        try:
            audio_segment = dialog_manager.synthesize_speech(text)
            buf = BytesIO()
            audio_segment.export(buf, format="wav")
            buf.seek(0)
            return send_file(buf, mimetype="audio/wav"), 200
        except Exception as e:
            logger.exception("Ошибка синтеза речи: %s", e)
            return jsonify({"error": "Ошибка синтеза речи."}), 500

    @app.route("/ping", methods=["GET"])
    def ping():
        return "pong", 200

    @app.route("/", methods=["GET"])
    def index():
        user_id = (request.args.get("user_id") or "guest").strip()
        logger.info("Запрос главной страницы для user_id=%r", user_id)
        try:
            entries = dialog_manager.history.fetch_latest(user_id=user_id, limit=30)
            messages = []
            for entry in reversed(entries):
                messages.append({"sender": "user", "text": entry["user"]})
                messages.append({"sender": "bot", "text": entry["assistant"]})
            return render_template("index.html", messages=messages)
        except Exception as e:
            logger.exception("Ошибка при рендеринге главной страницы: %s", e)
            return render_template("index.html", messages=[]), 500
