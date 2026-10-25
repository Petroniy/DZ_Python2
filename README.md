# Primitive DB

Консольная база данных на Python 3.12. Поддерживает создание таблиц, добавление,
выборку, обновление и удаление записей. Данные сохраняются между запусками.

## Установка и запуск

Из папки проекта:

```console
uv sync --locked
uv run database
uv run ruff check .
```

Также доступны команды `uv run project` и `uv run python -m primitive_db.main`.

Если используете Poetry:

```console
poetry install
poetry run database
poetry run ruff check .
```

Для окружения с Make доступны `make install`, `make run`, `make lint`
и `make build`. На Windows можно пользоваться командами uv напрямую.

## Управление таблицами

```text
create_table users name:str age:int is_active:bool
list_tables
info users
drop_table users
```

Типы столбцов: `int`, `str`, `bool`. Столбец `ID:int` добавляется первым
автоматически. Его значения вводить и изменять не нужно.

## CRUD-операции

```text
insert into users values ("Sergei", 28, true)
select from users
select from users where age = 28
update users set age = 29, is_active = false where name = "Sergei"
delete from users where ID = 1
```

Строки заключаются в одинарные или двойные кавычки. Значения `true` и `false`
обозначают логический тип, целые числа вводятся без кавычек. Все поля обязательны.
Количество значений в `insert` должно совпадать с количеством столбцов без ID.

В `where` поддерживается одно равенство. В `set` можно перечислить несколько
полей через запятую. Пробелы, запятые и знаки `=` внутри строк сохраняются:

```text
insert into users values ("Anna, from the sales team", 24, false)
```

Команда `help` показывает справку, `exit` завершает работу.
Некорректная команда выводит ошибку, после чего можно продолжить ввод.

## Декораторы и кэш

Ошибки обрабатывает `handle_db_errors`. Перед `delete` и `drop_table`
запрашивается подтверждение: операция выполняется только после ответа `y`.
Любой другой ответ, в том числе пустой, отменяет её.

Декоратор `log_time` выводит длительность `insert` и `select`.
Повторные одинаковые выборки используют кэш в замыкании `create_cacher`.
Изменения данных сбрасывают кэш. Полученный результат выборки можно менять,
не затрагивая сохранённое значение кэша.

## Хранение данных

В текущей рабочей папке создаются `db_meta.json` со схемами таблиц и каталог
`data/` с отдельным JSON-файлом для каждой таблицы. При удалении таблицы
её файл также удаляется. Эти файлы исключены из Git.

Сохранение выполняется через временный файл и замену исходного. Повреждённый
JSON не заменяется пустыми данными: программа сообщает об ошибке.

## Структура

```text
src/primitive_db/
    __init__.py
    main.py
    engine.py
    core.py
    utils.py
    parser.py
    decorators.py
    constants.py
```

Код написан функциями. Для ввода используется `prompt`, для вывода таблиц —
`prettytable`. Ruff находится в зависимостях разработки.

## Сборка

```console
uv build
uvx twine check dist/*
```

Собранный wheel можно установить в отдельное окружение или как CLI-инструмент:

```console
uv tool install dist/primitive_db-0.1.0-py3-none-any.whl
database
```

## Демонстрация

[![asciicast](https://asciinema.org/a/AzjxsiAQaOHkFDWs.svg)](https://asciinema.org/a/AzjxsiAQaOHkFDWs)

[Запись полного сценария в формате asciicast](docs/demo.cast)

Запись показывает установку окружения, создание таблицы, все CRUD-операции,
повторную выборку, ошибку типа, отмену и подтверждение удаления записей и таблицы.
Локальный файл можно воспроизвести командой `asciinema play docs/demo.cast`.
