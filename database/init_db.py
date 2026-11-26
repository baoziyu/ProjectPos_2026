"""Initialize a database and add missing demo products without changing existing rows."""

import argparse
from pathlib import Path

from src.infrastructure.sqlite_store import SQLiteStore

DEFAULT_PATH = Path(__file__).resolve().with_name("pos.sqlite3")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    SQLiteStore(args.database).initialize(seed=True)
    print(f"Initialized {args.database.resolve()}")


if __name__ == "__main__":
    main()
