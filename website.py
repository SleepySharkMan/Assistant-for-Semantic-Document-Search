from flask import request, jsonify, send_file, render_template
from io import BytesIO


def register_routes(app, dialog_manager):
    """
    Регистрирует API-маршруты Flask-приложения для работы с DialogManager.
    """

    @app.route("/api/message", methods=["POST"])
    def handle_text_message():
        data = request.get_json()
        question = data.get("message", "").strip()
        user_id = data.get("user_id", "").strip()

        if not user_id:
            return jsonify({"error": "user_id обязателен"}), 400
        if not question:
            return jsonify({"answer": "Вопрос не может быть пустым."}), 400

        answer = dialog_manager.answer_text(user_id=user_id, question=question)
        return jsonify({"answer": answer})

    @app.route("/api/history", methods=["GET"])
    def get_history():
        user_id = request.args.get("user_id", "").strip()
        if not user_id:
            return jsonify({"error": "user_id обязателен"}), 400

        history = dialog_manager.history.fetch_latest(user_id=user_id, limit=30)
        messages = []
        for entry in reversed(history):
            messages.append({"sender": "user", "text": entry["user"]})
            messages.append({"sender": "bot", "text": entry["assistant"]})
        return jsonify({"messages": messages})
    
    @app.route("/api/history", methods=["DELETE"])
    def delete_history():
        data = request.get_json()
        user_id = data.get("user_id", "").strip()
        if not user_id:
            return jsonify({"error": "user_id обязателен"}), 400

        dialog_manager.history.clear_user_history(user_id)
        return jsonify({"success": True})

    @app.route("/api/speech-to-text", methods=["POST"])
    def handle_speech_to_text():
        if "audio" not in request.files:
            return jsonify({"error": "Аудиофайл не предоставлен."}), 400

        audio = request.files["audio"]
        text = dialog_manager.answer_speech(audio.stream)
        return jsonify({"text": text or "Ошибка распознавания речи."})

    @app.route("/api/text-to-speech", methods=["POST"])
    def handle_text_to_speech():
        data = request.get_json()
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "Текст не может быть пустым."}), 400

        audio_stream = dialog_manager.synthesize_speech(text)
        return send_file(
            BytesIO(audio_stream.read()),
            mimetype="audio/wav",
            as_attachment=False
        )

    @app.route("/ping")
    def ping():
        return "pong"

    @app.route("/")
    def index():
        user_id = request.args.get("user_id", "guest")
        history = dialog_manager.history.fetch_latest(user_id=user_id, limit=30)
        messages = []
        for entry in reversed(history):
            messages.append({"sender": "user", "text": entry["user"]})
            messages.append({"sender": "bot", "text": entry["assistant"]})
        return render_template("index.html", messages=messages)
    
    
