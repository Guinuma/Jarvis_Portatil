"""Conversão e cópia de ficheiros locais."""
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from .project_files import safe_path

COMMAND = re.compile(r'(comprime|extrai|converte|copia) "([^"]+)" para "([^"]+)"[.!]?', re.I)


def extract_archive(source, target):
    with zipfile.ZipFile(source) as archive:
        members = archive.infolist()
        if len(members) > 1000 or sum(member.file_size for member in members) > 100_000_000:
            raise ValueError("O arquivo excede o limite de extração.")
        seen = set()
        for member in members:
            name = PurePosixPath(member.filename)
            if (name.is_absolute() or not name.parts or ".." in name.parts
                    or "\\" in member.filename or ":" in member.filename
                    or str(name).casefold() in seen or member.external_attr >> 28 == 0xA):
                raise ValueError("O arquivo contém um caminho incompatível com a extração.")
            seen.add(str(name).casefold())
        target.mkdir()
        try:
            for member in members:
                path = safe_path(target, member.filename)
                if member.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as reader, path.open("xb") as writer:
                        shutil.copyfileobj(reader, writer)
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile):
            shutil.rmtree(target)
            raise


def archive_command(text, root):
    match = COMMAND.fullmatch(text)
    if not match:
        return None
    action = match[1].casefold()
    source, target = (safe_path(root, name) for name in match.groups()[1:])
    if not source.is_file():
        raise ValueError("Indica um ficheiro de origem existente.")
    if action == "extrai":
        extract_archive(source, target)
    elif action == "comprime":
        if target.suffix.lower() != ".zip":
            raise ValueError("Indica um destino com extensão .zip.")
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(source, source.name)
    elif action == "copia":
        with source.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    else:
        if source.suffix.lower() != ".txt" or target.suffix.lower() != ".md":
            raise ValueError("A conversão disponível é de texto simples (.txt) para Markdown (.md).")
        body = source.read_text(encoding="utf-8-sig")
        with target.open("x", encoding="utf-8") as writer:
            writer.write(body)
    return f"Resultado em {target.relative_to(root)}."
