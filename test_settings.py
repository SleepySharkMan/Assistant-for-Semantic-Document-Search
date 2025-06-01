from flask import Flask, render_template, request, redirect, url_for
import json
import os

app = Flask(__name__)

# Default configuration (could be loaded from a file or database)
default_config = {
    "embedding_handler": {
        "device": "cpu",
        "model_path": "/path/to/embedding/model"
    },
    "response_generator": {
        "device": "cuda:0",
        "quantization": "fp16",
        "generation_mode": "stochastic",
        "text_model_path": "/path/to/text/model",
        "qa_model_path": "/path/to/qa/model",
        "generation_settings": {
            "max_new_tokens": 100,
            "num_sequences": 1,
            "ngram_repeat_ban": 3,
            "repetition_penalty": 1.2,
            "early_stopping": "yes",
            "cpu_offload": "no",
            "deterministic": {
                "num_beams": 5,
                "length_penalty": 1.0,
                "ngram_repeat_ban": 3
            },
            "stochastic": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50,
                "typical_p": 0.95,
                "num_beams": 1
            }
        }
    },
    "text_splitter": {
        "method": "by_sentences",
        "by_words": {"context_words": 100, "overlap_words": 20},
        "by_sentences": {"context_sentences": 5, "overlap_sentences": 1},
        "by_paragraphs": {"context_paragraphs": 2, "overlap_lines": 1}
    },
    "document_manager": {
        "processing": {"image_processing": "enabled", "allowed_extensions": ".pdf,.docx,.txt"},
        "image_captions": {"device": "cuda:0", "model_name": "caption_model"}
    },
    "embedding_storage": {
        "db_path": "/path/to/db",
        "collection_name": "embeddings",
        "embedding_dim": 768,
        "similarity_threshold": 0.8
    },
    "database": {"url": "sqlite:///database.db"},
    "speech_handler": {"language": "ru", "model": "/path/to/speech/model"},
    "document_folder": {"path": "/path/to/documents"},
    "dialog_manager": {
        "prompt_template": "USER: Вот информация:\n{context}\n\nВопрос: {question}\nПомоги мне, пожалуйста. Ответ:\nASSISTANT:",
        "show_text_source": "yes",
        "show_text_fragments": "yes",
        "messages": {
            "empty_storage": "Хранилище знаний пусто.",
            "context_not_found": "Подходящий контекст не найден."
        }
    },
    "logging": {
        "level": "INFO",
        "file": "/path/to/logfile.log",
        "max_size_bytes": 10485760,
        "backup_count": 5,
        "console_level": "WARNING"
    }
}

# Load or save config to a file
CONFIG_FILE = "config.json"

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return default_config

@app.route("/settings", methods=["GET", "POST"])
def config_interface():
    config = load_config()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "reset":
            config = default_config
            save_config(config)
        elif action == "optimize":
            pass   # здесь будет логика оптимизации
        else:
            config["embedding_handler"]["device"] = request.form.get("embedding_device")
            config["embedding_handler"]["model_path"] = request.form.get("embedding_model_path")
            save_config(config)
        return redirect(url_for("config_interface"))

    return render_template(
        "settings/settings_layout.html",
        config=config
    )

if __name__ == "__main__":
    app.run(debug=True)