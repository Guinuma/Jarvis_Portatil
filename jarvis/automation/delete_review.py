"""Rever e confirmar a eliminação de um ficheiro local individual."""
import hashlib
import json
import os
import re
from pathlib import Path
from uuid import uuid4

from jarvis.integrations.project_files import SKIP, safe_path

PREPARE = re.compile(r'(?:prepara (?:a )?eliminação permanente de|elimina permanentemente) "([^"\r\n]{1,500})"[.!]?', re.I)
APPROVE = re.compile(r'confirma (?:a )?eliminação (\d{1,18}) com ([a-f0-9]{8})[.!]?', re.I)
CANCEL = re.compile(r'(?:cancela|recusa) (?:a )?eliminação (\d{1,18})[.!]?', re.I)
STATUS = re.compile(r'(?:mostra|verifica) (?:a )?eliminação (\d{1,18})[.!]?', re.I)
MAX_BYTES = 128 * 1024 * 1024


def delete_command(text, memory, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := PREPARE.fullmatch(command):
        return prepare(memory, root, match[1])
    if match := APPROVE.fullmatch(command):
        row = request_row(memory, int(match[1]))
        return apply(memory, root, row, match[2].lower())
    if match := CANCEL.fullmatch(command):
        row = memory.execute(
            """UPDATE delete_reviews SET state='cancelada'
               WHERE id=? AND state='a rever' RETURNING id""", (int(match[1]),),
        )
        return "Eliminação cancelada." if row else "Essa eliminação não está a aguardar confirmação."
    if match := STATUS.fullmatch(command):
        row = request_row(memory, int(match[1]))
        return f"Eliminação {row['id']} · {row['state']} · {row['path']}" + (f"\n{row['detail']}" if row["detail"] else "")
    return None


def authorized_file(root, name):
    raw = Path(name)
    if raw.anchor or not raw.parts or any(part.startswith(".") or part in SKIP or ":" in part for part in raw.parts):
        raise ValueError("Indica um ficheiro normal numa pasta autorizada do projeto.")
    target = safe_path(root, name)
    if target != root / raw or target.is_symlink() or not target.is_file():
        raise ValueError("O ficheiro está indisponível ou o caminho não corresponde ao original.")
    return target


def fingerprint(path):
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        stats = os.fstat(stream.fileno())
        if stats.st_size > MAX_BYTES:
            raise ValueError("O ficheiro excede o limite de 128 MB para revisão.")
        for chunk in iter(lambda: stream.read(1_048_576), b""):
            count += len(chunk)
            if count > MAX_BYTES:
                raise ValueError("O ficheiro excede o limite de 128 MB para revisão.")
            digest.update(chunk)
        final = os.fstat(stream.fileno())
    if final.st_size != count or final.st_mtime_ns != stats.st_mtime_ns:
        raise ValueError("O ficheiro mudou durante a revisão. Prepara outra revisão.")
    return [stats.st_dev, stats.st_ino, count, stats.st_mtime_ns, digest.hexdigest()]


def prepare(memory, root, name):
    target = authorized_file(root, name)
    path = target.relative_to(root).as_posix()
    checked = fingerprint(target)
    token = uuid4().hex
    row = memory.execute(
        "INSERT INTO delete_reviews (path, token, fingerprint) VALUES (?, ?, ?) RETURNING id",
        (path, token, json.dumps(checked)),
    )[0]
    return (f"Revisão {row['id']} · eliminação permanente de {path}\n"
            f"{checked[2]} bytes · SHA-256 {checked[4]}\n"
            f"Para confirmar, pede «Confirma a eliminação {row['id']} com {token[:8]}».\n"
            f"Para recusar, pede «Cancela a eliminação {row['id']}».")


def request_row(memory, identifier):
    rows = memory.execute("SELECT * FROM delete_reviews WHERE id=?", (identifier,))
    if not rows:
        raise ValueError("Não encontrei essa revisão de eliminação.")
    return rows[0]


def finish(memory, identifier, state, detail):
    memory.execute("UPDATE delete_reviews SET state=?, detail=? WHERE id=? AND state='em curso'",
                   (state, detail, identifier))
    return detail


def apply(memory, root, row, code):
    if row["state"] != "a rever" or row["token"][:8] != code:
        raise ValueError("A revisão de eliminação ou o código deixaram de estar disponíveis.")
    path = authorized_file(root, row["path"])
    expected = json.loads(row["fingerprint"])
    if fingerprint(path) != expected:
        memory.execute(
            "UPDATE delete_reviews SET state='desatualizada' WHERE id=? AND state='a rever'", (row["id"],),
        )
        raise ValueError("O ficheiro mudou desde a revisão. Prepara uma nova confirmação.")
    claim = memory.execute(
        """UPDATE delete_reviews SET state='em curso'
           WHERE id=? AND state='a rever' AND token=? RETURNING id""", (row["id"], row["token"]),
    )
    if not claim:
        raise ValueError("A confirmação já foi usada ou cancelada.")
    holding = path.parent / (".jarvis-delete-" + row["token"])
    staged = holding / path.name
    try:
        holding.mkdir()
        if authorized_file(root, row["path"]) != path:
            raise ValueError("O caminho mudou depois da confirmação.")
        path.rename(staged)
        if staged.is_symlink() or fingerprint(staged) != expected:
            raise ValueError("A versão separada para eliminação diverge da revisão.")
        staged.unlink()
    except (OSError, ValueError, RuntimeError):
        try:
            if staged.is_symlink():
                return finish(memory, row["id"], "a verificar",
                              f"A operação foi interrompida. Verifica o caminho {holding.relative_to(root)}.")
            if staged.exists():
                os.link(staged, path)
                staged.unlink()
        except OSError:
            return finish(memory, row["id"], "a verificar",
                          f"A operação foi interrompida. Ficou um ficheiro em {holding.relative_to(root)}.")
        return finish(memory, row["id"], "recusada", "A operação foi interrompida e a eliminação foi recusada.")
    finally:
        try:
            holding.rmdir()
        except OSError:
            pass
    return finish(memory, row["id"], "eliminada", f"Ficheiro eliminado permanentemente · {row['path']}.")
