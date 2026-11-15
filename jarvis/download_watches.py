"""Acompanhar a chegada de downloads à pasta configurada no perfil local."""
import json
import os
import re
import time

from .downloads import downloads_root
from .integrations.project_files import safe_path

WATCH = re.compile(
    r'(?:jarvis,\s*)?avisa-me quando o download(?: (?:de )?"([^"\r\n]+)")? acabar[.!]?',
    re.I,
)
CANCEL = re.compile(r'cancela o aviso de download (\d{1,18})[.!]?', re.I)
PARTIALS = (".crdownload", ".part", ".download")
QUIET_SECONDS = 5


def watch_command(text, memory):
    match = WATCH.fullmatch(text)
    cancel = CANCEL.fullmatch(text)
    if cancel:
        row = memory.execute(
            """UPDATE download_watches SET status='cancelado'
               WHERE id=? AND status='pendente' RETURNING name""", (int(cancel[1]),),
        )
        return f"Aviso cancelado para {row[0]['name']}." if row else "Não há um aviso pendente com esse número."
    if not match:
        return None
    root = downloads_root()
    if not root.is_dir():
        raise ValueError("A pasta de Downloads está indisponível.")
    name = match[1]
    if name is None:
        candidates = sorted({
            path.name[:-len(suffix)] for path in root.iterdir() for suffix in PARTIALS
            if path.name.casefold().endswith(suffix) and path.is_file() and not path.is_symlink()
        }, key=str.casefold)
        if len(candidates) == 1 and not candidates[0].casefold().startswith("unconfirmed "):
            name = candidates[0]
        else:
            options = "\n".join(f'«Avisa-me quando o download "{item}" acabar»' for item in candidates[:10]
                                if not item.casefold().startswith("unconfirmed "))
            reply = 'Indica o nome final do download, por exemplo «Avisa-me quando o download "relatorio.pdf" acabar».'
            return reply + ("\n" + options if options else "")

    target = download_path(root, name)
    baseline = signature(target)
    if baseline and not has_partial(root, name):
        return f"{name} já está na pasta de Downloads. Para vigiar outro download, indica o nome do ficheiro em curso."
    rows = memory.execute(
        """INSERT INTO download_watches (root, name, baseline) VALUES (?, ?, ?)
           ON CONFLICT DO NOTHING RETURNING id""",
        (str(root), name, baseline),
    )
    if not rows:
        return f"Já existe um aviso pendente para {name}."
    return f"Aviso {rows[0]['id']} guardado. Vou avisar quando {name} estiver disponível em Downloads."


def download_path(root, name):
    if (not name.strip() or len(name) > 240 or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.endswith((" ", ".")) or name.casefold().endswith(PARTIALS)
            or getattr(os.path, "isreserved", lambda name: False)(name)):
        raise ValueError("Indica apenas o nome final do ficheiro, incluindo a extensão.")
    path = root / name
    if path.is_symlink() or safe_path(root, name) != path:
        raise ValueError("O download tem de estar diretamente na pasta autorizada.")
    return path


def signature(path):
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return json.dumps([stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]) if path.is_file() else None


def has_partial(root, name):
    return any((root / (name + suffix)).exists() for suffix in PARTIALS)


def check_download_watches(memory):
    root = downloads_root()
    now = time.time()
    rows = memory.execute("SELECT * FROM download_watches WHERE root=? AND status='pendente'", (str(root),))
    for row in rows:
        try:
            observed = signature(download_path(root, row["name"]))
            if has_partial(root, row["name"]) or observed == row["baseline"]:
                observed = None
        except (OSError, RuntimeError, ValueError):
            observed = None
        if observed != row["observed"]:
            memory.execute(
                """UPDATE download_watches SET observed=?, observed_at=?
                   WHERE id=? AND status='pendente' AND observed IS ? AND observed_at IS ?""",
                (observed, now if observed else None, row["id"], row["observed"], row["observed_at"]),
            )
        elif observed and now - row["observed_at"] >= QUIET_SECONDS:
            memory.execute(
                """UPDATE download_watches SET status='concluído', finished=?
                   WHERE id=? AND status='pendente' AND observed=? AND observed_at=?""",
                (now, row["id"], observed, row["observed_at"]),
            )


def download_updates(memory):
    # Keep the completed record visible after the one-time announcement is claimed.
    alerts = memory.execute(
        """UPDATE download_watches SET announced=1
           WHERE status='concluído' AND announced=0 RETURNING id, name"""
    )
    watches = memory.execute(
        """SELECT id, name, status FROM download_watches
           WHERE status='pendente' OR id IN (
               SELECT id FROM download_watches WHERE status<>'pendente' ORDER BY id DESC LIMIT 10
           ) ORDER BY id DESC"""
    )
    return {"alerts": alerts, "watches": watches}
