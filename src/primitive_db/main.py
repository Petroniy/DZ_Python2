#!/usr/bin/env python3

from primitive_db import engine


def main():
    """Запускает консольную базу данных."""
    engine.run()


if __name__ == "__main__":
    main()
