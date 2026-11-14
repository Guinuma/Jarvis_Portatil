"""Pré-visualizar e aplicar movimentos em Downloads."""
import json
import os
import re
from pathlib import Path

from .integrations.project_files import safe_path

CATEGORIES = {
    ".pdf": "Documentos", ".txt": "Documentos", ".docx": "Documentos",
    ".jpg": "Imagens", ".jpeg": "Imagens", ".png": "Imagens",
    ".zip": "Arquivos", ".7z": "Arquivos",
}


def downloads_command(text, memory):
    command = text.casefold().rstrip(".!?")
    approval = re.fullmatch(r"aprova o plano de downloads (\d+)", command)
    if command != "previsualiza a organização de downloads" and not approval:
        return None
    root = Path(os.environ.get("JARVIS_DOWNLOADS_DIR") or Path.home() / "Downloads").resolve(strict=True)
    if command == "previsualiza a organização de downloads":
        files = []
        for path in sorted(root.iterdir()):
            category = CATEGORIES.get(path.suffix.casefold())
            if category and path.is_file() and not path.is_symlink():
                target = safe_path(root, f"{category}/{path.name}")
                if not target.exists():
                    stat = path.stat()
                    files.append((path.name, target.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns))
            if len(files) == 30:
                break
        if not files:
            return "Não encontrei ficheiros para organizar em Downloads."
        row = memory.execute(
            "INSERT INTO download_plans(root, files) VALUES (?, ?) RETURNING id",
            (str(root), json.dumps(files, ensure_ascii=False)),
        )[0]
        moves = "\n".join(f"{source} → {target}" for source, target, _, _ in files)
        return f"Plano {row['id']}:\n{moves}\nPara aplicar: «Aprova o plano de Downloads {row['id']}»."
    rows = memory.execute(
        "UPDATE download_plans SET claimed=1 WHERE id=? AND root=? AND claimed=0 RETURNING files",
        (int(approval[1]), str(root)),
    )
    if not rows:
        return "O plano não existe ou já foi usado."
    results = []
    for source_name, target_name, size, timestamp in json.loads(rows[0]["files"]):
        try:
            source = safe_path(root, source_name)
            target = safe_path(root, target_name)
            stat = source.stat()
            if (source != root / source_name or target != root / target_name
                    or (stat.st_size, stat.st_mtime_ns) != (size, timestamp)):
                raise ValueError("ficheiro alterado desde a pré-visualização")
            target.parent.mkdir(exist_ok=True)
            os.link(source, target)
            try:
                source.unlink()
            except OSError:
                target.unlink()
                raise
            results.append(f"Movido: {target_name}")
        except (OSError, ValueError, RuntimeError):
            results.append(f"Ignorado: {source_name} (ficheiro alterado, indisponível ou destino ocupado)")
    return "\n".join(results)
