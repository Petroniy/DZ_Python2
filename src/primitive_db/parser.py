import shlex


def _tokenize(text):
    """Разбирает команду, сохраняя строковые значения в кавычках."""
    if "\x00" in text:
        raise ValueError("Недопустимый символ в команде.")
    literals = {}
    protected = []
    position = 0
    while position < len(text):
        char = text[position]
        if char not in ("'", '"'):
            protected.append(char)
            position += 1
            continue
        quote = char
        position += 1
        value = []
        while position < len(text) and text[position] != quote:
            char = text[position]
            if char == "\\" and position + 1 < len(text):
                following = text[position + 1]
                if following in (quote, "\\"):
                    value.append(following)
                    position += 2
                    continue
            value.append(char)
            position += 1
        if position == len(text):
            raise ValueError("Не закрыты кавычки в строковом значении.")
        marker = f"\x00{len(literals)}\x00"
        literals[marker] = "".join(value)
        protected.append(marker)
        position += 1
    lexer = shlex.shlex("".join(protected), posix=True, punctuation_chars="(),=")
    lexer.whitespace_split = True
    lexer.commenters = ""
    tokens = []
    for token in lexer:
        if token in literals:
            tokens.append((literals[token], True))
        elif "\x00" in token:
            raise ValueError("Между аргументами нужен пробел или разделитель.")
        elif token and all(char in "(),=" for char in token):
            tokens.extend((char, False) for char in token)
        else:
            tokens.append((token, False))
    return tokens


def _keyword(token, expected):
    """Проверяет служебное слово вне кавычек."""
    return not token[1] and token[0].lower() == expected


def _identifier(token):
    """Проверяет имя таблицы или столбца."""
    name, quoted = token
    if quoted or not name.isidentifier():
        raise ValueError(f"Некорректное имя: {name}.")
    return name


def _value(token):
    """Преобразует литерал в int, str или bool."""
    value, quoted = token
    if quoted:
        return value
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    digits = value[1:] if value.startswith(("+", "-")) else value
    if digits and digits.isdecimal():
        return int(value)
    raise ValueError(f"Некорректное значение: {value}. Строки заключайте в кавычки.")


def _values(tokens):
    """Разбирает непустой список значений через запятую."""
    if not tokens or len(tokens) % 2 == 0:
        raise ValueError("Ожидается непустой список значений через запятую.")
    result = []
    for position, token in enumerate(tokens):
        if position % 2:
            if token != (",", False):
                raise ValueError("Между значениями нужна запятая.")
        else:
            result.append(_value(token))
    return result


def _assignments(tokens, multiple=False):
    """Разбирает пары столбец = значение."""
    if not tokens or (len(tokens) + 1) % 4:
        raise ValueError("Ожидается условие вида столбец = значение.")
    if not multiple and len(tokens) != 3:
        raise ValueError("В where поддерживается одно условие равенства.")
    result = {}
    for position in range(0, len(tokens), 4):
        name = _identifier(tokens[position])
        if name in result:
            raise ValueError(f"Столбец {name} указан несколько раз.")
        if tokens[position + 1] != ("=", False):
            raise ValueError("Между столбцом и значением нужен знак =.")
        result[name] = _value(tokens[position + 2])
        if position + 3 < len(tokens) and tokens[position + 3] != (",", False):
            raise ValueError("Между изменяемыми столбцами нужна запятая.")
    return result


def parse_values(text):
    """Возвращает список значений из части values."""
    tokens = _tokenize(text)
    if tokens and _keyword(tokens[0], "values"):
        tokens = tokens[1:]
    if tokens and tokens[0] == ("(", False):
        if tokens[-1] != (")", False):
            raise ValueError("Не закрыта скобка списка values.")
        tokens = tokens[1:-1]
    return _values(tokens)


def parse_where(text):
    """Возвращает словарь для условия where."""
    tokens = _tokenize(text)
    if tokens and _keyword(tokens[0], "where"):
        tokens = tokens[1:]
    return _assignments(tokens)


def parse_set(text):
    """Возвращает словарь изменяемых полей."""
    tokens = _tokenize(text)
    if tokens and _keyword(tokens[0], "set"):
        tokens = tokens[1:]
    return _assignments(tokens, multiple=True)


def parse_command(text):
    """Разбирает полную команду консольной базы данных."""
    tokens = _tokenize(text)
    if not tokens:
        return {"command": ""}
    command = _identifier(tokens[0]).lower()
    result = {"command": command}
    if command in ("help", "exit", "list_tables"):
        if len(tokens) != 1:
            raise ValueError(f"Команда {command} не принимает аргументов.")
    elif command in ("drop_table", "info"):
        if len(tokens) != 2:
            raise ValueError(f"Использование: {command} <имя_таблицы>.")
        result["table"] = _identifier(tokens[1])
    elif command == "create_table":
        if len(tokens) < 3:
            raise ValueError("Укажите имя таблицы и хотя бы один столбец:тип.")
        result["table"] = _identifier(tokens[1])
        if any(quoted for _, quoted in tokens[2:]):
            raise ValueError("Схема таблицы задаётся без кавычек.")
        result["columns"] = [value for value, _ in tokens[2:]]
    elif command == "insert":
        if (
            len(tokens) < 7
            or not _keyword(tokens[1], "into")
            or not _keyword(tokens[3], "values")
            or tokens[4] != ("(", False)
            or tokens[-1] != (")", False)
        ):
            raise ValueError(
                "Использование: insert into <таблица> values (<значения>)."
            )
        result["table"] = _identifier(tokens[2])
        result["values"] = _values(tokens[5:-1])
    elif command == "select":
        if len(tokens) < 3 or not _keyword(tokens[1], "from"):
            raise ValueError("Использование: select from <таблица> [where <условие>].")
        result["table"] = _identifier(tokens[2])
        result["where"] = None
        if len(tokens) > 3:
            if not _keyword(tokens[3], "where"):
                raise ValueError("После имени таблицы ожидается where.")
            result["where"] = _assignments(tokens[4:])
    elif command == "update":
        if len(tokens) < 10 or not _keyword(tokens[2], "set"):
            raise ValueError(
                "Использование: update <таблица> set <поля> where <условие>."
            )
        result["table"] = _identifier(tokens[1])
        positions = [
            position
            for position in range(3, len(tokens))
            if _keyword(tokens[position], "where")
        ]
        if len(positions) != 1:
            raise ValueError("Для update требуется одно условие where.")
        boundary = positions[0]
        result["set"] = _assignments(tokens[3:boundary], multiple=True)
        result["where"] = _assignments(tokens[boundary + 1 :])
    elif command == "delete":
        if (
            len(tokens) < 7
            or not _keyword(tokens[1], "from")
            or not _keyword(tokens[3], "where")
        ):
            raise ValueError("Использование: delete from <таблица> where <условие>.")
        result["table"] = _identifier(tokens[2])
        result["where"] = _assignments(tokens[4:])
    else:
        raise ValueError(f"Функции {command} нет. Попробуйте снова.")
    return result
