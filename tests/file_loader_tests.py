import pytest
import os
import tempfile
import pandas as pd
from FileLoader import FileLoader


@pytest.fixture
def temp_dir():
    """Создание временной директории для тестовых файлов"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


@pytest.fixture
def loader():
    """Создание экземпляра FileLoader для тестов"""
    return FileLoader()


@pytest.fixture
def sample_files(temp_dir):
    """Создание тестовых файлов разных форматов"""
    # Создаем текстовый файл
    txt_path = os.path.join(temp_dir, "test.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("Test content")

    # Создаем CSV файл
    csv_path = os.path.join(temp_dir, "test.csv")
    pd.DataFrame({'A': [1, 2, 3]}).to_csv(csv_path, index=False)

    return {
        'txt': txt_path,
        'csv': csv_path,
        'dir': temp_dir
    }


def test_init():
    """Тест инициализации класса"""
    # Тест с дефолтными форматами
    loader = FileLoader()
    assert sorted(loader.get_allowed_formats()) == sorted(
        ['.txt', '.pdf', '.docx', '.csv', '.xlsx'])

    # Тест с пользовательскими форматами
    custom_formats = ['.json', '.xml']
    loader = FileLoader(custom_formats)
    assert loader.get_allowed_formats() == custom_formats


def test_add_allowed_format(loader):
    """Тест добавления нового формата"""
    # Добавление нового формата
    assert loader.add_allowed_format('.json') is True
    assert '.json' in loader.get_allowed_formats()

    # Попытка добавить существующий формат
    assert loader.add_allowed_format('.json') is False

    # Добавление формата без точки
    assert loader.add_allowed_format('xml') is True
    assert '.xml' in loader.get_allowed_formats()


def test_remove_allowed_format(loader):
    """Тест удаления формата"""
    # Удаление существующего формата
    assert loader.remove_allowed_format('.txt') is True
    assert '.txt' not in loader.get_allowed_formats()

    # Попытка удаления несуществующего формата
    assert loader.remove_allowed_format('.json') is False

    # Попытка удалить все форматы
    formats = loader.get_allowed_formats()
    for fmt in formats[:-1]:  # Оставляем последний формат
        assert loader.remove_allowed_format(fmt) is True
    # Не должны иметь возможность удалить последний формат
    assert loader.remove_allowed_format(formats[-1]) is False


def test_add_file(loader, sample_files):
    """Тест добавления файла"""
    # Добавление существующего файла правильного формата
    assert loader.add_file(sample_files['txt']) is True
    assert sample_files['txt'] in loader.get_file_list()

    # Повторное добавление того же файла
    assert loader.add_file(sample_files['txt']) is False

    # Попытка добавить несуществующий файл
    assert loader.add_file('nonexistent.txt') is False


def test_add_files_from_folder(loader, sample_files):
    """Тест добавления файлов из папки"""
    # Добавление файлов из существующей папки
    added = loader.add_files_from_folder(sample_files['dir'])
    assert added == 2  # должно быть добавлено 2 файла (txt и csv)

    # Попытка добавить файлы из несуществующей папки
    assert loader.add_files_from_folder('nonexistent_folder') == 0


def test_remove_file(loader, sample_files):
    """Тест удаления файла"""
    # Сначала добавляем файл
    loader.add_file(sample_files['txt'])

    # Удаление существующего файла
    assert loader.remove_file(sample_files['txt']) is True
    assert sample_files['txt'] not in loader.get_file_list()

    # Попытка удалить несуществующий файл
    assert loader.remove_file('nonexistent.txt') is False


def test_remove_files_from_folder(loader, sample_files):
    """Тест удаления файлов из папки"""
    # Сначала добавляем файлы
    loader.add_files_from_folder(sample_files['dir'])

    # Удаление файлов из папки
    removed = loader.remove_files_from_folder(sample_files['dir'])
    assert removed == 2
    assert len(loader.get_file_list()) == 0


def test_get_file_list(loader, sample_files):
    """Тест получения списка файлов"""
    # Добавляем файлы разных форматов
    loader.add_file(sample_files['txt'])
    loader.add_file(sample_files['csv'])

    # Получение всех файлов
    all_files = loader.get_file_list()
    assert len(all_files) == 2

    # Фильтрация по формату
    txt_files = loader.get_file_list('txt')
    assert len(txt_files) == 1
    assert sample_files['txt'] in txt_files


def test_clear_file_list(loader, sample_files):
    """Тест очистки списка файлов"""
    # Добавляем несколько файлов
    loader.add_file(sample_files['txt'])
    loader.add_file(sample_files['csv'])

    # Очищаем список
    assert loader.clear_file_list() is True
    assert len(loader.get_file_list()) == 0


def test_get_file_content(loader, sample_files):
    """Тест получения содержимого файла"""
    # Добавляем текстовый файл
    loader.add_file(sample_files['txt'])

    # Получаем содержимое существующего файла
    content = loader.get_file_content(sample_files['txt'])
    assert content == "Test content"

    # Попытка получить содержимое файла, которого нет в списке
    assert loader.get_file_content('nonexistent.txt') is None


def test_save_and_load_file_list(loader, sample_files, temp_dir):
    """Тест сохранения и загрузки списка файлов"""
    # Добавляем файлы
    loader.add_file(sample_files['txt'])
    loader.add_file(sample_files['csv'])

    # Сохраняем список
    json_path = os.path.join(temp_dir, 'file_list.json')
    loader.save_file_list(json_path)

    # Создаем новый загрузчик и загружаем список
    new_loader = FileLoader()
    new_loader.load_file_list(json_path)

    # Проверяем, что списки файлов идентичны
    assert sorted(loader.get_file_list()) == sorted(new_loader.get_file_list())
