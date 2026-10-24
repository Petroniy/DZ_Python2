import json

from primitive_db.constants import ID_COLUMN, ID_SCHEMA, PYTHON_TYPES, VALID_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data

_cache_result = create_cacher()


def _validate_name(name, kind):
    """Проверить имя таблицы или столбца."""
    if not isinstance(name, str) or not name.isidentifier():
        raise ValueError(f"Некорректное имя {kind}: {name}.")


def _parse_columns(columns):
    """Преобразовать определения столбцов в словарь типов."""
    if not isinstance(columns, (list, tuple)):
        raise ValueError("Столбцы должны быть списком определений имя:тип.")
    schema = {}
    for column in columns:
        if not isinstance(column, str) or column.count(":") != 1:
            raise ValueError(f"Некорректное определение столбца: {column}.")
        name, type_name = column.split(":")
        _validate_name(name, "столбца")
        if name in schema:
            raise ValueError(f'Столбец "{name}" указан несколько раз.')
        if type_name not in VALID_TYPES:
            raise ValueError(f"Неизвестный тип данных: {type_name}.")
        if name == ID_COLUMN and type_name != "int":
            raise ValueError("Столбец ID должен иметь тип int.")
        schema[name] = type_name
    return schema


def _table_schema(metadata, table_name):
    """Найти схему существующей таблицы."""
    _validate_name(table_name, "таблицы")
    if table_name not in metadata:
        raise KeyError(table_name)
    schema = _parse_columns(metadata[table_name])
    if schema.get(ID_COLUMN) != "int":
        raise ValueError("В схеме таблицы отсутствует ID:int.")
    return schema


def _validate_value(name, value, type_name):
    """Проверить обязательное значение по объявленному типу."""
    if type(value) is not PYTHON_TYPES[type_name]:
        raise ValueError(f'Столбец "{name}" должен иметь тип {type_name}.')
    if type_name == "str" and not value.strip():
        raise ValueError(f'Столбец "{name}" не может быть пустым.')


def _data_schema(table_data, columns):
    """Взять схему из метаданных либо определить её по первой записи."""
    if not isinstance(table_data, list) or any(
        not isinstance(row, dict) for row in table_data
    ):
        raise ValueError("Данные таблицы должны быть списком записей.")
    if columns is not None:
        schema = _parse_columns(columns)
    elif table_data:
        schema = {}
        for name, value in table_data[0].items():
            _validate_name(name, "столбца")
            type_name = type(value).__name__
            if type_name not in VALID_TYPES:
                raise ValueError(f'Неизвестный тип у столбца "{name}".')
            schema[name] = type_name
    else:
        return None
    for row in table_data:
        if row.keys() != schema.keys():
            raise ValueError("Набор полей записи не соответствует схеме.")
        for name, type_name in schema.items():
            _validate_value(name, row[name], type_name)
    return schema


def _validate_clause(clause, schema, required=False, updating=False):
    """Проверить поля и типы условия или присваивания."""
    if not required and (clause is None or clause == {}):
        return
    if not isinstance(clause, dict) or not clause:
        raise ValueError("Нужно указать непустое условие или присваивание.")
    for name, value in clause.items():
        _validate_name(name, "столбца")
        if updating and name == ID_COLUMN:
            raise ValueError("Изменять ID нельзя.")
        if schema is not None:
            if name not in schema:
                raise KeyError(name)
            _validate_value(name, value, schema[name])
        elif type(value).__name__ not in VALID_TYPES:
            raise ValueError(f'Некорректное значение столбца "{name}".')


def _matches(row, where_clause):
    """Проверить все равенства условия."""
    return not where_clause or all(
        row[name] == value and type(row[name]) is type(value)
        for name, value in where_clause.items()
    )


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Добавить таблицу со служебным столбцом ID."""
    _validate_name(table_name, "таблицы")
    if table_name in metadata:
        raise ValueError(f'Таблица "{table_name}" уже существует.')
    schema = _parse_columns(columns)
    if not schema or set(schema) == {ID_COLUMN}:
        raise ValueError("Укажите хотя бы один столбец кроме ID.")
    metadata[table_name] = [ID_SCHEMA] + [
        f"{name}:{type_name}" for name, type_name in schema.items() if name != ID_COLUMN
    ]
    _cache_result.clear()
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удалить схему таблицы после подтверждения."""
    _table_schema(metadata, table_name)
    del metadata[table_name]
    _cache_result.clear()
    return metadata


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Добавить запись с автоматически вычисленным ID."""
    schema = _table_schema(metadata, table_name)
    fields = [name for name in schema if name != ID_COLUMN]
    if not isinstance(values, (list, tuple)) or len(values) != len(fields):
        raise ValueError(f"Ожидалось значений: {len(fields)}.")
    row = {}
    for name, value in zip(fields, values):
        _validate_value(name, value, schema[name])
        row[name] = value
    table_data = load_table_data(table_name)
    _data_schema(table_data, metadata[table_name])
    identifiers = [item[ID_COLUMN] for item in table_data]
    if any(identifier < 1 for identifier in identifiers) or len(
        set(identifiers)
    ) != len(identifiers):
        raise ValueError("В таблице найдены некорректные или повторяющиеся ID.")
    row = {ID_COLUMN: max(identifiers, default=0) + 1, **row}
    table_data.append(row)
    _cache_result.clear()
    return table_data


@handle_db_errors
@log_time
def select(table_data, where_clause=None, columns=None):
    """Вернуть записи, соответствующие условию, с кэшированием запроса."""
    schema = _data_schema(table_data, columns)
    _validate_clause(where_clause, schema)
    key = json.dumps(
        [table_data, where_clause, columns], ensure_ascii=False, sort_keys=True
    )
    result = _cache_result(
        key,
        lambda: [dict(row) for row in table_data if _matches(row, where_clause)],
    )
    return json.loads(json.dumps(result, ensure_ascii=False))


@handle_db_errors
def update(table_data, set_clause, where_clause, columns=None):
    """Обновить выбранные записи после проверки всех значений."""
    schema = _data_schema(table_data, columns)
    _validate_clause(set_clause, schema, required=True, updating=True)
    _validate_clause(where_clause, schema, required=True)
    result = []
    for row in table_data:
        updated_row = dict(row)
        if _matches(row, where_clause):
            updated_row.update(set_clause)
        result.append(updated_row)
    _cache_result.clear()
    return result


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause, columns=None):
    """Удалить записи по условию после подтверждения."""
    schema = _data_schema(table_data, columns)
    _validate_clause(where_clause, schema, required=True)
    result = [dict(row) for row in table_data if not _matches(row, where_clause)]
    _cache_result.clear()
    return result
