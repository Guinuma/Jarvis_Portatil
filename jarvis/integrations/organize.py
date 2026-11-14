"""Operações de organização de ficheiros no projeto local."""
import hashlib
import os
import re
from collections import defaultdict
from pathlib import Path

from .project_files import SKIP, safe_path

MOVE = re.compile(r'(renomeia|move) (?:o ficheiro )?"([^"]+)" para "([^"]+)"[.!]?', re.I)


def duplicates(root):
    by_size = defaultdict(list)
    for folder, dirs, names in os.walk(root):
        parent = Path(folder)
        dirs[:] = [name for name in dirs if name not in SKIP and
                   (parent / name).resolve().parent == parent]
        for name in names:
            path = parent / name
            if not path.is_symlink() and path.resolve().parent == parent and path.is_file():
                by_size[path.stat().st_size].append(path)
    by_hash = defaultdict(list)
    for paths in by_size.values():
        if len(paths) < 2:
            continue
        for path in paths:
            with path.open("rb") as source:
                fingerprint = hashlib.file_digest(source, "sha256").hexdigest()
            by_hash[fingerprint].append(path.relative_to(root).as_posix())
    return sorted(sorted(paths) for paths in by_hash.values() if len(paths) > 1)


def organize_files(text, root):
    match = MOVE.fullmatch(text)
    if match:
        source = safe_path(root, match[2])
        if not source.is_file():
            raise ValueError("Indica um ficheiro existente.")
        destination = safe_path(root, match[3])
        if match[1].casefold() == "renomeia":
            if Path(match[3]).name != match[3]:
                raise ValueError("Para renomear, indica apenas o novo nome.")
            destination = safe_path(root, str((source.parent / match[3]).relative_to(root)))
        # A ligação rígida reserva o destino sem sobrescrever um ficheiro existente.
        os.link(source, destination)
        try:
            source.unlink()
        except OSError:
            destination.unlink()
            raise
        return f"Ficheiro em {destination.relative_to(root)}."
    if text.casefold().rstrip(".!?") in {"encontra duplicados", "mostra ficheiros duplicados"}:
        groups = duplicates(root)
        if not groups:
            return "Não encontrei ficheiros duplicados."
        return "Duplicados por conteúdo (SHA-256):\n" + "\n".join(" · ".join(group) for group in groups[:20])
    return None
