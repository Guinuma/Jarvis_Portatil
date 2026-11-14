"""Abrir projetos autorizados no Visual Studio Code."""
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

OPEN_PROJECT = re.compile(
    r"(?:jarvis[, ]+)?(?:abre|abrir) (?:o )?"
    r"(?:(?:meu )?projeto(?: jarvis portatil)?|jarvis portatil)"
    r"(?: no (?:vs code|vscode|visual studio code))?[.!?]*"
)


def is_open_project_request(text):
    normalized = unicodedata.normalize("NFD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return bool(OPEN_PROJECT.fullmatch(" ".join(normalized.split())))


def open_project(folder):
    editor = shutil.which("Code.exe")
    if not editor and (command := shutil.which("code.cmd")):
        candidate = Path(command).resolve().parent.parent / "Code.exe"
        if candidate.is_file():
            editor = str(candidate)
    if not editor:
        raise FileNotFoundError("Instala o VS Code e adiciona o comando code ao PATH.")
    subprocess.Popen([editor, str(folder)], cwd=folder)
