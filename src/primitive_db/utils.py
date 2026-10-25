import json
import os

from primitive_db.constants import DATA_DIR, META_FILE


def _load_json(filepath, default):
    """Прочитать JSON, вернув начальное значение только для нового файла."""
    try:
        with open(filepath, encoding="utf-8") as source:
            return json.load(source)
    except FileNotFoundError:
        return default


def _save_json(filepath, data):
    """Сохранить JSON через временный файл."""
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary_path = f"{filepath}.tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as target:
            json.dump(data, target, ensure_ascii=False, indent=2)
            target.write("\n")
        os.replace(temporary_path, filepath)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def _table_path(table_name):
    """Получить путь к файлу таблицы с безопасным именем."""
    if not isinstance(table_name, str) or not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}.")
    return os.path.join(DATA_DIR, f"{table_name}.json")


def load_metadata(filepath=META_FILE):
    """Загрузить схемы таблиц или пустой словарь для новой базы."""
    metadata = _load_json(filepath, {})
    if not isinstance(metadata, dict):
        raise ValueError("Файл метаданных должен содержать словарь.")
    return metadata


def save_metadata(filepath, data):
    """Сохранить схемы таблиц."""
    if not isinstance(data, dict):
        raise ValueError("Метаданные должны быть словарём.")
    _save_json(filepath, data)


def load_table_data(table_name):
    """Загрузить записи таблицы или пустой список для нового файла."""
    data = _load_json(_table_path(table_name), [])
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError("Файл таблицы должен содержать список записей.")
    return data


def save_table_data(table_name, data):
    """Сохранить записи таблицы."""
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ValueError("Данные таблицы должны быть списком записей.")
    _save_json(_table_path(table_name), data)


def remove_table_data(table_name):
    """Удалить файл таблицы, если он существует."""
    filepath = _table_path(table_name)
    if os.path.exists(filepath):
        os.remove(filepath)
