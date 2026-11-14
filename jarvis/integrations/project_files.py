"""Pesquisa e escrita de notas dentro de pastas de projeto."""
import os
import re
import tempfile
from datetime import date
from pathlib import Path

from .editor import normalize, open_project, resolve_project

COMMAND = re.compile(
    r"(?:jarvis[, ]+)?(encontra (?:o )?ficheiro|procura (?:por )?conteudo|"
    r"abre (?:o )?ficheiro|cria (?:o )?ficheiro|guarda (?:uma )?nota) (.+)"
)
TEXT_TYPES = {".md", ".txt", ".csv", ".json", ".py", ".js", ".html", ".vtt", ".srt"}
SKIP = {".git", ".venv", "node_modules", "__pycache__", "vendor"}


def safe_path(root, name):
    relative = Path(name.strip('"'))
    if relative.anchor:
        raise ValueError("Indica um caminho relativo ao projeto.")
    path = (root / relative).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("O caminho está fora do projeto autorizado.")
    return path


def search(root, query, content):
    matches = []
    for folder, dirs, files in os.walk(root):
        parent = Path(folder)
        dirs[:] = sorted(name for name in dirs if name not in SKIP and
                        (parent / name).resolve().parent == parent)
        for name in sorted(files):
            path = parent / name
            if path.resolve().parent != parent or path.is_symlink():
                continue
            if content:
                if path.suffix.lower() not in TEXT_TYPES:
                    continue
                try:
                    with path.open(encoding="utf-8", errors="replace") as stream:
                        found = query.casefold() in stream.read(256_000).casefold()
                except OSError:
                    continue
            else:
                found = query.casefold() in name.casefold()
            if found:
                matches.append(path.relative_to(root).as_posix())
                if len(matches) == 20:
                    return matches
    return matches


def file_command(text, root):
    scoped = re.fullmatch(r'(.+?) no projeto "([^"]+)"[.!]?', text, re.I)
    if scoped and COMMAND.fullmatch(normalize(scoped[1])):
        projects = resolve_project(scoped[2], root)
        if not projects:
            raise ValueError('Projeto não autorizado.')
        if len(projects) > 1:
            return 'Escolhe o projeto pelo caminho completo:\n' + '\n'.join(
                f'{scoped[1]} no projeto "{path}"' for _, path in projects)
        folder = projects[0][1]
        if not folder.is_dir():
            raise ValueError('O projeto autorizado está indisponível.')
        reply = file_command(scoped[1], folder)
        if reply and reply.startswith('Ficheiros encontrados'):
            reply = '\n'.join(line + f' no projeto "{folder}"' if line.startswith('Abre o ficheiro') else line for line in reply.splitlines())
        return reply
    match = COMMAND.fullmatch(normalize(text))
    if not match:
        return None
    action = match[1]
    value = text[match.start(2):].strip()
    if action.startswith(("encontra", "procura")):
        matches = search(root, value.strip('"'), action.startswith("procura"))
        if not matches:
            return "Não encontrei ficheiros que correspondam ao pedido."
        return "Ficheiros encontrados. Para abrir, usa um destes pedidos:\n" + "\n".join(
            f'Abre o ficheiro "{path}"' for path in matches
        )
    if action.startswith("guarda"):
        folder = safe_path(root, f"notes/{date.today():%Y-%m-%d}")
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=folder, prefix="nota-", suffix=".md", delete=False
        ) as stream:
            stream.write(value + "\n")
            path = Path(stream.name)
        return f"Nota guardada em {path.relative_to(root)}."
    path = safe_path(root, value)
    if action.startswith("cria"):
        with path.open("x", encoding="utf-8"):
            pass
        return f"Ficheiro criado em {path.relative_to(root)}."
    if path.suffix.lower() not in TEXT_TYPES or not path.is_file():
        raise ValueError("Escolhe um ficheiro de texto existente no projeto.")
    open_project(root, target=path)
    return f"Pedi ao VS Code para abrir {path.relative_to(root)}."
