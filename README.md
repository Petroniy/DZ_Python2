# База данных

Учебная база данных на Python. Работает через команды в терминале,
таблицы и записи сохраняются в JSON.

Установка и запуск:

```console
uv sync
uv run database
```

Проверка кода: `uv run ruff check .`.
Через Poetry: `poetry install`, затем `poetry run database`.

## Управление таблицами

```text
create_table users name:str age:int is_active:bool
list_tables
info users
```

Типы: `int`, `str`, `bool`. Столбец ID добавляется автоматически.

## CRUD-операции

```text
insert into users values ("Sergei", 28, true)
select from users
select from users where age = 28
update users set age = 29, is_active = false where name = "Sergei"
delete from users where ID = 1
```

Удалить таблицу: `drop_table users`.

Строки вводятся в кавычках, числа и `true`/`false` — без кавычек.
`help` показывает справку, `exit` завершает программу.

При ошибке выводится сообщение, программа продолжает работу.
Для удаления записи или таблицы нужно подтвердить действие ответом `y`.
Для `insert` и `select` выводится время выполнения.
Повторные выборки берутся из кэша, при изменении данных кэш сбрасывается.

Запись работы:

[![asciicast](https://asciinema.org/a/AzjxsiAQaOHkFDWs.svg)](https://asciinema.org/a/AzjxsiAQaOHkFDWs)

