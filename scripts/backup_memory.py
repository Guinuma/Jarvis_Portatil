"""Criar uma cópia SQLite ou restaurá-la para um novo perfil."""
import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from jarvis.app import local_memory
from jarvis.memory import Memory


def copy_database(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
        tables = {row[0] for row in original.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"memories", "routines"} <= tables:
            raise ValueError("A origem não é uma base de dados de memória e rotinas do JARVIS.")
        with destination.open("xb"):
            pass
        try:
            with closing(sqlite3.connect(destination)) as restored:
                original.backup(restored)
        except BaseException:
            destination.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--restore-to", metavar="PERFIL")
    args = parser.parse_args()
    memory = local_memory()
    try:
        if args.restore_to:
            target = Memory(memory.path.parent, args.restore_to).path
            copy_database(args.file, target)
        else:
            target = args.file
            copy_database(memory.path, target)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")
    print(f"Cópia SQLite criada em {target}.")


if __name__ == "__main__":
    main()
