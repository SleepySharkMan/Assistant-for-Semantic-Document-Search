import os


def call_message(client, user_id: str, message: str, info: str = None):
    """
    Отправляет POST-запрос на /api/message и печатает JSON-ответ в консоль.

    client: Flask test_client
    info может быть:
      - 'source' для включения информации об источниках,
      - 'fragments' для включения текстовых фрагментов,
      - 'all' для включения и того, и другого.
    """
    payload = {'user_id': user_id, 'message': message}
    if info:
        key = info.lower()
        if key in ('source', 'all'):
            payload['show_source_info'] = True
        if key in ('fragments', 'all'):
            payload['show_text_fragments'] = True
    resp = client.post('/api/message', json=payload)
    print('POST /api/message ->', resp.status_code)
    print(resp.get_json())


def call_get_history(client, user_id: str):
    """
    Отправляет GET-запрос на /api/history и печатает JSON-ответ в консоль.
    """
    resp = client.get('/api/history', query_string={'user_id': user_id})
    print('GET /api/history ->', resp.status_code)
    print(resp.get_json())


def call_delete_history(client, user_id: str):
    """
    Отправляет DELETE-запрос на /api/history и печатает JSON-ответ в консоль.
    """
    resp = client.delete('/api/history', json={'user_id': user_id})
    print('DELETE /api/history ->', resp.status_code)
    print(resp.get_json())


def call_speech_to_text(client, user_id: str, audio_path: str):
    """
    Отправляет POST-запрос на /api/speech-to-text с файлом WAV и печатает JSON-ответ.
    """
    if not os.path.isfile(audio_path):
        print(f'Файл не найден: {audio_path}')
        return

    with open(audio_path, 'rb') as f:
        data = {'user_id': user_id, 'audio': (f, os.path.basename(audio_path))}
        resp = client.post('/api/speech-to-text', data=data)
        print('POST /api/speech-to-text ->', resp.status_code)
        print(resp.get_json())


def call_text_to_speech(client, user_id: str, text: str, output_path: str = 'output.wav'):
    """
    Отправляет POST-запрос на /api/text-to-speech, сохраняет WAV в файл и печатает информацию.
    """
    payload = {'user_id': user_id, 'text': text}
    resp = client.post('/api/text-to-speech', json=payload)
    print('POST /api/text-to-speech ->', resp.status_code)
    if resp.status_code == 200:
        with open(output_path, 'wb') as out:
            out.write(resp.data)
        print(f'Аудио сохранено в {output_path} (размер {len(resp.data)} байт)')
    else:
        print(resp.get_json())


def call_ping(client):
    """
    Проверяет доступность сервиса через /ping.
    """
    resp = client.get('/ping')
    print('GET /ping ->', resp.status_code)
    print(resp.data.decode())


def call_index(client, user_id: str = None):
    """
    Запрашивает главную страницу и печатает HTML-код.
    """
    qs = {'user_id': user_id} if user_id else {}
    resp = client.get('/', query_string=qs)
    print('GET / ->', resp.status_code)
    print(resp.get_data(as_text=True))


if __name__ == '__main__':
    from main import create_app
    # Создаём приложение и client только здесь
    app = create_app()
    client = app.test_client()

    # Примеры использования:
    call_ping(client)
    call_index(client, 'test_user')
    call_message(client, 'test_user', 'Привет, как дела?', info='source')
    call_message(client, 'test_user', 'Где найти документацию?', info='fragments')
    call_message(client, 'test_user', 'Расскажи подробно', info='all')
    call_get_history(client, 'test_user')
    call_delete_history(client, 'test_user')
    # Для распознавания речи укажите путь к существующему WAV файлу:
    # call_speech_to_text(client, 'test_user', 'path/to/audio.wav')
    call_text_to_speech(client, 'test_user', 'Текст для синтеза речи')
