import os
import json

from typing import Optional, List
from config_models import AppConfig


class FileLoader:
    def __init__(self, config: AppConfig):
        self.allowed_formats = config.allowed_formats
        self.files = []

    def update_config(self, new_config: AppConfig):
        self.allowed_formats = new_config.allowed_formats

    def get_allowed_formats(self):
        return self.allowed_formats.copy()

    def get_file_list(self, filter_format: Optional[str] = None) -> List[str]:
        if not filter_format:
            return self.files.copy()
        if not filter_format.startswith('.'):
            filter_format = '.' + filter_format
        return [
            file for file in self.files
            if os.path.splitext(file)[1].lower() == filter_format
        ]

    def add_file(self, file_path: str) -> bool:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in self.allowed_formats:
            print(f"Формат файла {file_ext} не поддерживается")
            return False
        if not os.path.exists(file_path):
            print("Файл не существует")
            return False
        if file_path in self.files:
            print("Файл уже добавлен")
            return False
        self.files.append(file_path)
        return True

    def add_files_from_folder(self, folder_path: str) -> int:
        if not os.path.exists(folder_path):
            print(f"Папка '{folder_path}' не существует")
            return 0
        if not os.path.isdir(folder_path):
            print(f"Путь '{folder_path}' не является папкой")
            return 0
        added_count = 0
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                if self.add_file(file_path):
                    added_count += 1
        return added_count

    def remove_file(self, file_path: str) -> bool:
        if file_path not in self.files:
            print(f"Файл '{file_path}' отсутствует в списке")
            return False
        self.files.remove(file_path)
        print(f"Файл '{file_path}' удален из списка")
        return True

    def remove_files_from_folder(self, folder_path: str) -> int:
        folder_path = os.path.abspath(folder_path)
        removed_count = 0
        new_files = []
        for file_path in self.files:
            if os.path.abspath(os.path.dirname(file_path)) == folder_path:
                removed_count += 1
            else:
                new_files.append(file_path)
        self.files = new_files
        return removed_count

    def clear_file_list(self) -> bool:
        self.files.clear()
        print("Список файлов успешно очищен.")
        return True

    def save_file_list(self, output_path='file_list.json'):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.files, f)

    def load_file_list(self, input_path='file_list.json'):
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                loaded_files = json.load(f)
                self.files = [f for f in loaded_files if os.path.exists(f)]
        except FileNotFoundError:
            print("Файл списка не найден")
