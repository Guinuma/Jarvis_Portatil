"""Propor uma edição textual localizada e aplicar a versão revista."""
import codecs
import hashlib
import json
import os
import re
import tempfile
from difflib import unified_diff
from pathlib import Path
from threading import Lock

from .code_tools import CODE_TYPES
from .project_files import safe_path

PROPOSE = re.compile(r'propõe alteração em "([^"]+)" com (.+)', re.I | re.S)
DECIDE = re.compile(r'(aplica|descarta) (?:a )?proposta (\d{1,18})[.!]?', re.I)
APPLY_LOCK = Lock()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def code_path(root, name):
    path = safe_path(root, name)
    if (path.suffix.lower() not in CODE_TYPES or not path.is_file()
            or path.stat().st_size > 512_000
            or any(part.startswith(".") for part in path.relative_to(root).parts)):
        raise ValueError("Indica um ficheiro de código autorizado com até 512 kB.")
    return path


def replace_once(content, old, new):
    encoding = "utf-8-sig" if content.startswith(codecs.BOM_UTF8) else "utf-8"
    text = content.decode(encoding)
    if "\x00" in text:
        raise ValueError("Indica um ficheiro de texto UTF-8.")
    if "\r\n" in text and "\n" not in text.replace("\r\n", ""):
        old, new = [value.replace("\r\n", "\n").replace("\n", "\r\n") for value in (old, new)]
    if text.count(old) != 1:
        raise ValueError("O trecho original precisa de corresponder a uma única ocorrência.")
    result = text.replace(old, new, 1)
    if result == text:
        raise ValueError("A proposta não altera o ficheiro.")
    return result.encode(encoding), text, result


def proposal_command(text, memory, root):
    proposal = PROPOSE.fullmatch(text)
    decision = DECIDE.fullmatch(text)
    if not proposal and not decision:
        return None
    if proposal:
        path = code_path(root, proposal[1])
        name = path.relative_to(root).as_posix()
        values = json.loads(proposal[2])
        if not isinstance(values, dict) or set(values) != {"antes", "depois"}:
            raise ValueError('Indica a alteração como {"antes":"texto atual","depois":"texto novo"}.')
        old, new = values["antes"], values["depois"]
        if not isinstance(old, str) or not old or not isinstance(new, str):
            raise ValueError("Indica um trecho original e o texto de substituição.")
        content = path.read_bytes()
        after, original_text, changed_text = replace_once(content, old, new)
        diff = "\n".join(unified_diff(original_text.splitlines(), changed_text.splitlines(),
                                      fromfile=name, tofile=name, lineterm=""))
        if not diff or len(diff) > 7000:
            raise ValueError("A alteração não cabe numa pré-visualização completa. Usa um trecho mais pequeno.")
        row = memory.execute(
            """INSERT INTO code_proposals (root, path, old_text, new_text, before_hash, after_hash)
               VALUES (?, ?, ?, ?, ?, ?) RETURNING id""",
            (str(root), name, old, new, digest(content), digest(after)),
        )[0]
        identifier = row["id"]
        return f"Proposta {identifier}\n{diff}\n\nPara aprovar: «Aplica a proposta {identifier}»."

    identifier = int(decision[2])
    with APPLY_LOCK:
        rows = memory.execute(
            "SELECT * FROM code_proposals WHERE id=? AND root=? AND status='a rever'", (identifier, str(root)),
        )
        if not rows:
            raise ValueError("A proposta não existe ou já foi decidida.")
        row = rows[0]
        if decision[1].casefold() == "descarta":
            memory.execute("UPDATE code_proposals SET status='descartada' WHERE id=?", (identifier,))
            return f"Proposta {identifier} descartada."
        path = code_path(root, row["path"])
        content = path.read_bytes()
        current_hash = digest(content)
        if current_hash == row["after_hash"]:
            memory.execute("UPDATE code_proposals SET status='aplicada' WHERE id=?", (identifier,))
            return f"O ficheiro já contém a versão proposta: {row['path']}."
        if current_hash != row["before_hash"]:
            memory.execute("UPDATE code_proposals SET status='desatualizada' WHERE id=?", (identifier,))
            raise ValueError("O ficheiro mudou desde a revisão. Prepara uma proposta nova.")
        after, _, _ = replace_once(content, row["old_text"], row["new_text"])
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(after)
        try:
            os.chmod(temporary, path.stat().st_mode & 0o777)
            if code_path(root, row["path"]) != path or path.read_bytes() != content:
                raise ValueError("O ficheiro mudou antes da escrita. Prepara uma proposta nova.")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        memory.execute("UPDATE code_proposals SET status='aplicada' WHERE id=?", (identifier,))
        return f"Proposta {identifier} aplicada a {row['path']}."
