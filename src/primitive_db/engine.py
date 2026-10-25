import prompt
from prettytable import PrettyTable

from primitive_db import core
from primitive_db.constants import COMMAND_PROMPT, ID_COLUMN, META_FILE
from primitive_db.decorators import handle_db_errors
from primitive_db.parser import parse_command
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    remove_table_data,
    save_metadata,
    save_table_data,
)


def welcome():
    """Выводит приветствие при запуске."""
    print("\n***База данных***")
    print_help()


def print_help():
    """Показывает доступные команды."""
    print("\nУправление таблицами:")
    print("  create_table <таблица> <столбец:тип> ... — создать таблицу")
    print("  list_tables — показать все таблицы")
    print("  drop_table <таблица> — удалить таблицу")
    print("\nОперации с данными:")
    print("  insert into <таблица> values (<значение>, ...) — добавить запись")
    print("  select from <таблица> [where <столбец> = <значение>] — выбрать записи")
    print("  update <таблица> set <столбец> = <значение> where <условие> — изменить")
    print("  delete from <таблица> where <столбец> = <значение> — удалить записи")
    print("  info <таблица> — показать структуру и количество записей")
    print("\nТипы: int, str, bool. Строковые значения вводятся в кавычках.")
    print("  help — справка")
    print("  exit — выход")


def _table_exists(metadata, table_name):
    """Проверяет таблицу до загрузки данных и подтверждения."""
    if table_name not in metadata:
        print(f'Ошибка: Таблица "{table_name}" не существует.')
        return False
    return True


def _print_rows(rows, columns):
    """Печатает строки таблицы в порядке столбцов схемы."""
    fields = [column.split(":", 1)[0] for column in columns]
    table = PrettyTable()
    table.field_names = fields
    for row in rows:
        table.add_row([row[field] for field in fields])
    print(table)


def _matching_ids(rows, where_clause):
    """Сохраняет номера подходящих записей для сообщения о результате."""
    return [
        row[ID_COLUMN]
        for row in rows
        if all(
            type(row.get(field)) is type(value) and row.get(field) == value
            for field, value in where_clause.items()
        )
    ]


@handle_db_errors
def execute_command(metadata, command):
    """Выполняет разобранную команду и сохраняет успешные изменения."""
    name = command["command"]
    if name == "help":
        print_help()
        return
    if name == "list_tables":
        if not metadata:
            print("В базе пока нет таблиц.")
        for table_name in metadata:
            print(f"- {table_name}")
        return
    table_name = command["table"]
    if name == "create_table":
        result = core.create_table(metadata, table_name, command["columns"])
        if result is not None:
            save_table_data(table_name, [])
            save_metadata(META_FILE, result)
            columns = ", ".join(result[table_name])
            print(f'Таблица "{table_name}" успешно создана со столбцами: {columns}')
        return
    if not _table_exists(metadata, table_name):
        return
    if name == "drop_table":
        result = core.drop_table(metadata, table_name)
        if result is not None:
            remove_table_data(table_name)
            save_metadata(META_FILE, result)
            print(f'Таблица "{table_name}" успешно удалена.')
        return
    if name == "insert":
        result = core.insert(metadata, table_name, command["values"])
        if result is not None:
            save_table_data(table_name, result)
            record_id = result[-1][ID_COLUMN]
            print(
                f'Запись с ID={record_id} успешно добавлена в таблицу "{table_name}".'
            )
        return
    rows = load_table_data(table_name)
    if rows is None:
        return
    columns = metadata[table_name]
    if name == "info":
        print(f"Таблица: {table_name}")
        print(f"Столбцы: {', '.join(columns)}")
        print(f"Количество записей: {len(rows)}")
    elif name == "select":
        result = core.select(rows, command["where"], columns=columns)
        if result is not None:
            _print_rows(result, columns)
    elif name == "update":
        record_ids = _matching_ids(rows, command["where"])
        result = core.update(rows, command["set"], command["where"], columns=columns)
        if result is not None:
            if record_ids:
                save_table_data(table_name, result)
                for record_id in record_ids:
                    print(
                        f'Запись с ID={record_id} в таблице "{table_name}" '
                        "успешно обновлена."
                    )
            else:
                print("Записи для обновления не найдены.")
    elif name == "delete":
        matching_rows = core.select(rows, command["where"], columns=columns)
        if matching_rows is None:
            return
        record_ids = [row[ID_COLUMN] for row in matching_rows]
        result = core.delete(rows, command["where"], columns=columns)
        if result is not None:
            if record_ids:
                save_table_data(table_name, result)
                for record_id in record_ids:
                    print(
                        f"Запись с ID={record_id} успешно удалена "
                        f'из таблицы "{table_name}".'
                    )
            else:
                print("Записи для удаления не найдены.")


def run():
    """Запускает цикл ввода команд до exit или конца ввода."""
    welcome()
    while True:
        try:
            user_input = prompt.string(f"\n{COMMAND_PROMPT}", empty=True)
            if user_input is None or not user_input.strip():
                continue
            command = parse_command(user_input)
            if command["command"] == "exit":
                print("До свидания!")
                break
            if not command["command"]:
                continue
            metadata = load_metadata()
            if metadata is not None:
                execute_command(metadata, command)
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break
        except ValueError as error:
            message = str(error)
            if message.startswith("Функции "):
                print(message)
            else:
                print(f"Ошибка валидации: {message}")
        except OSError as error:
            print(f"Ошибка работы с файлом: {error}")
