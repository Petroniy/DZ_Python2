import time

import prompt


def _preserve_metadata(wrapper, function):
    """Сохраняет имя и описание оборачиваемой функции."""
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    wrapper.__wrapped__ = function
    return wrapper


def handle_db_errors(function):
    """Выводит понятное сообщение об ошибке операции."""

    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except FileNotFoundError:
            print(
                "Ошибка: Файл данных не найден. "
                "Возможно, база данных не инициализирована."
            )
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except OSError as error:
            print(f"Ошибка работы с файлом: {error}")
        except Exception as error:
            print(f"Произошла непредвиденная ошибка: {error}")
        return None

    return _preserve_metadata(wrapper, function)


def confirm_action(action_name):
    """Запрашивает подтверждение перед изменением данных."""

    def decorator(function):
        def wrapper(*args, **kwargs):
            try:
                answer = prompt.string(
                    f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ',
                    empty=True,
                )
            except (EOFError, KeyboardInterrupt):
                print("Операция отменена.")
                return None
            if answer != "y":
                print("Операция отменена.")
                return None
            return function(*args, **kwargs)

        return _preserve_metadata(wrapper, function)

    return decorator


def log_time(function):
    """Печатает продолжительность вызова функции."""

    def wrapper(*args, **kwargs):
        started_at = time.monotonic()
        try:
            return function(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started_at
            print(f"Функция {function.__name__} выполнилась за {elapsed:.3f} секунд")

    return _preserve_metadata(wrapper, function)


def create_cacher():
    """Создаёт независимый кэш в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        """Возвращает сохранённый результат или вычисляет новый."""
        if key not in cache:
            cache[key] = value_func()
        return cache[key]

    cache_result.clear = cache.clear
    return cache_result
