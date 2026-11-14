"""Pesquisa de notas por data de sessão em pastas de projetos autorizados."""
import re
from datetime import date
from pathlib import Path

from .editor import normalize

REQUEST = re.compile(
    r"(?:jarvis[, ]+)?(?:encontra|procura|mostra) (?:as )?notas da ultima sessao(?: (?:do|de) projeto (.+))?"
)
SESSION_DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")


def notes_request(text):
    text = text.strip().rstrip(".!?").strip()
    match = REQUEST.fullmatch(normalize(text))
    if not match:
        return None
    return text[match.start(1):].strip('"') if match[1] else ""


def latest_notes(project):
    """Retorna a data e os caminhos relativos da sessão mais recente em notes/."""
    root = project / "notes"
    sessions = {}
    if root.is_symlink() or root.resolve().parent != project:
        return None, []
    for folder in root.iterdir() if root.is_dir() else ():
        if not SESSION_DATE.fullmatch(folder.name) or folder.is_symlink():
            continue
        try:
            session = date.fromisoformat(folder.name)
        except ValueError:
            continue
        if folder.resolve().parent != root or not folder.is_dir():
            continue
        files = [
            note.relative_to(project).as_posix()
            for note in folder.iterdir()
            if note.suffix.lower() in {".md", ".txt"}
            and not note.is_symlink() and note.resolve().parent == folder and note.is_file()
        ]
        if files:
            sessions[session] = sorted(files)
    if not sessions:
        return None, []
    latest = max(sessions)
    return latest, sessions[latest]
