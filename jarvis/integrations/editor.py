"""Abrir projetos autorizados no Visual Studio Code."""
import json
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

EDITOR_SUFFIX = r" no (?:vs code|vscode|visual studio code)"
OPEN_PROJECT = re.compile(
    rf"(?:jarvis[, ]+)?(?:abre|abrir) (?:o )?(?:meu )?projeto"
    rf"(?: (.+?))?(?:{EDITOR_SUFFIX})?"
)


def normalize(text):
    return "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(char)
    )


def project_request(text):
    command = text.strip().rstrip(".!?").strip()
    normalized = normalize(command)
    if re.fullmatch(rf"(?:jarvis[, ]+)?(?:abre|abrir) (?:o )?jarvis portatil(?:{EDITOR_SUFFIX})?", normalized):
        return ""
    match = OPEN_PROJECT.fullmatch(normalized)
    if not match:
        return None
    if match[1] is None or re.fullmatch(EDITOR_SUFFIX.strip(), match[1]):
        return ""
    # Recover the original spelling, including accents and spaces in paths.
    prefix = re.match(r"(?:jarvis[, ]+)?(?:abre|abrir) (?:o )?(?:meu )?projeto ", command, re.I)
    name = re.sub(EDITOR_SUFFIX + "$", "", command[prefix.end():], flags=re.I).strip()
    return name.strip('"')


def resolve_project(name, root):
    projects = [("JARVIS Portátil", root)]
    if not name:
        return projects
    config = os.environ.get("JARVIS_PROJECTS_FILE")
    if config:
        data = json.loads(Path(config).expanduser().read_text(encoding="utf-8-sig"))
        if not isinstance(data, list):
            raise ValueError("A lista de projetos deve ser um array.")
        for entry in data:
            label = entry["nome"]
            folder = Path(entry["pasta"]).expanduser()
            if not isinstance(label, str) or not label.strip() or not folder.is_absolute():
                raise ValueError("Cada projeto precisa de um nome e uma pasta absoluta.")
            projects.append((label, folder.resolve()))
    candidate = Path(name)
    if candidate.is_absolute():
        folder = candidate.resolve()
        return [(label, path) for path, label in {path: label for label, path in projects if path == folder}.items()]
    matches = {path: label for label, path in projects if normalize(label) == normalize(name)}
    return [(label, path) for path, label in matches.items()]


def open_project(folder, *, target=None, files=()):
    if not folder.is_dir():
        raise NotADirectoryError("A pasta autorizada deste projeto está indisponível.")
    editor = shutil.which("Code.exe")
    if not editor and (command := shutil.which("code.cmd")):
        candidate = Path(command).resolve().parent.parent / "Code.exe"
        if candidate.is_file():
            editor = str(candidate)
    if not editor:
        raise FileNotFoundError("Instala o VS Code e adiciona o comando code ao PATH.")
    subprocess.Popen([editor, str(target or folder), *(str(path) for path in files)], cwd=folder)
