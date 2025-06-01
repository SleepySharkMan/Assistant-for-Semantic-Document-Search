import logging
from itertools import zip_longest
from flask import request, jsonify, send_file, render_template
from io import BytesIO
from werkzeug.exceptions import NotFound
import mimetypes

logger = logging.getLogger(__name__)


def register_routes(app, dialog_manager):
    @app.errorhandler(Exception)
    def handle_global_exception(error):
        logger.exception("Uncaught exception: %s", str(error)[:100])
        if isinstance(error, NotFound):
            return jsonify({"error": "Not found."}), 404
        return jsonify({"error": "Internal server error."}), 500

    @app.route("/api/message", methods=["POST"])
    def handle_text_message():
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()[:50]
        question = (data.get("message") or "").strip()[:1000]
        show_src = bool(data.get("show_source_info"))
        show_frag = bool(data.get("show_text_fragments"))

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        if not question:
            return jsonify({"error": "Question cannot be empty."}), 400

        try:
            response = dialog_manager.answer_text(
                user_id=user_id,
                question=question,
                request_source_info=show_src,
                request_fragments=show_frag
            )
        except Exception as exc:
            return jsonify({"error": "Failed to process request.", "details": str(exc)[:100]}), 500

        answer = response.get("answer", "")
        if not isinstance(answer, str):
            answer = ""

        raw_frags = response.get("fragments")
        fragments = [f for f in raw_frags if isinstance(f, str)] if isinstance(raw_frags, list) else []

        source = response.get("source") or ""
        if not source and isinstance(response.get("sources"), list):
            candidates = [s for s in response["sources"] if isinstance(s, str) and s.strip()]
            source = candidates[0] if candidates else ""

        result = {"answer": answer}
        if fragments:
            result["fragments"] = fragments
        if source:
            result["source"] = source

        return jsonify(result), 200


    @app.route("/api/history", methods=["GET"])
    def get_history():
        user_id = (request.args.get("user_id") or "").strip()[:50]
        logger.info("HTTP %s %s user_id=%s",
                    request.method, request.path, user_id)

        if not user_id:
            logger.warning("Invalid history request: missing user_id. Parameters=%s", str(
                request.args)[:100])
            return jsonify({"error": "user_id is required"}), 400

        try:
            entries = dialog_manager.history.fetch_latest(
                user_id=user_id, limit=30)
            messages = []
            for entry in reversed(entries):
                messages.append({"sender": "user", "text": entry["user"]})
                messages.append({"sender": "bot", "text": entry["assistant"]})
            return jsonify({"messages": messages}), 200
        except Exception as e:
            logger.exception(
                "Error fetching history for user_id=%s: %s", user_id, str(e)[:100])
            return jsonify({"error": "Failed to fetch history.", "details": str(e)[:100]}), 500

    @app.route("/api/history", methods=["DELETE"])
    def delete_history():
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()[:50]
        logger.info("HTTP %s %s user_id=%s",
                    request.method, request.path, user_id)

        if not user_id:
            logger.warning(
                "Invalid history deletion request: missing user_id. Payload=%s", str(data)[:100])
            return jsonify({"error": "user_id is required"}), 400

        try:
            dialog_manager.history.clear_user_history(user_id)
            return jsonify({"success": True}), 200
        except Exception as e:
            logger.exception(
                "Error deleting history for user_id=%s: %s", user_id, str(e)[:100])
            return jsonify({"error": "Failed to delete history.", "details": str(e)[:100]}), 500

    @app.route("/api/speech-to-text", methods=["POST"])
    def handle_speech_to_text():
        user_id = (request.form.get("user_id") or request.args.get("user_id") or "").strip()[:50]
        logger.info("HTTP %s %s user_id=%s", request.method, request.path, user_id)

        if "audio" not in request.files:
            logger.warning("Invalid request: audio file missing. user_id=%s", user_id)
            return jsonify({"error": "Audio file is required."}), 400

        audio_file = request.files["audio"]
        max_size_mb = 10
        allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3"]
        content_type = mimetypes.guess_type(audio_file.filename)[0]
        audio_size = audio_file.content_length or 0

        if content_type not in allowed_types:
            logger.warning("Invalid audio format: %s for user_id=%s", content_type, user_id)
            return jsonify({"error": f"Invalid audio format. Allowed: {', '.join(allowed_types)}."}), 400
        if audio_size > max_size_mb * 1024 * 1024:
            logger.warning("Audio file too large: %s bytes for user_id=%s", audio_size, user_id)
            return jsonify({"error": f"Audio file exceeds {max_size_mb} MB limit."}), 400

        try:
            audio_data = audio_file.stream.read()
            text = dialog_manager.answer_speech(audio_data)
            if text is None:
                logger.error("Speech recognition returned None for user_id=%s", user_id)
                return jsonify({"error": "Speech recognition failed."}), 500
            return jsonify({"text": text}), 200
        except Exception as e:
            logger.exception("Speech recognition error for user_id=%s: %s", user_id, str(e)[:100])
            return jsonify({"error": "Speech recognition failed.", "details": str(e)[:100]}), 500

    @app.route("/ping", methods=["GET"])
    def ping():
        return "pong", 200

    @app.route("/", methods=["GET"])
    def index():
        user_id = (request.args.get("user_id") or "guest").strip()[:50]
        logger.info("Main page request for user_id=%s", user_id)
        try:
            entries = dialog_manager.history.fetch_latest(user_id=user_id, limit=30)
            messages = []
            for entry in reversed(entries):
                messages.append({"sender": "user", "text": entry["user"]})
                messages.append({"sender": "bot", "text": entry["assistant"]})
            return render_template(
                "chat/index.html",
                messages=messages,
                show_text_source_info=dialog_manager.show_text_source_info,
                show_text_fragments=dialog_manager.show_text_fragments
            )
        except Exception as e:
            logger.exception("Error rendering main page for user_id=%s: %s", user_id, str(e)[:100])
            return render_template(
                "chat/index.html",
                messages=messages,
                show_text_source_info=dialog_manager.show_text_source_info,
                show_text_fragments=dialog_manager.show_text_fragments
            ), 500
