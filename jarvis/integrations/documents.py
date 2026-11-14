"""Pesquisa de documentos PDF com referências por página."""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .project_files import SKIP, safe_path

SEARCH = re.compile(r'procura (?:nos|em) pdfs?( com ocr)? (.+)', re.I)


def pdf_command(text, root):
    summary = re.fullmatch(r'resume (?:o )?pdf "([^"]+)"[.!]?', text, re.I)
    match = SEARCH.fullmatch(text)
    if not match and not summary:
        return None
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as error:
        raise ValueError("Instala pypdf para pesquisar PDFs.") from error
    if summary:
        path = safe_path(root, summary[1])
        if path.suffix.lower() != ".pdf" or not path.is_file():
            raise ValueError("Indica um PDF existente no projeto.")
        excerpts = []
        try:
            with path.open("rb") as stream:
                for number, page in enumerate(PdfReader(stream).pages, 1):
                    body = " ".join((page.extract_text() or "").split())
                    if body:
                        sentences = re.split(r"(?<=[.!?])\s+", body, maxsplit=1)
                        excerpts.append(f"Página {number}: {sentences[0][:320]}")
                    if len(excerpts) == 5:
                        break
        except PdfReadError as error:
            raise ValueError("Não consegui ler o PDF.") from error
        if not excerpts:
            return "O PDF não contém texto selecionável. Experimenta a pesquisa com OCR."
        return f"Resumo por excertos de {path.relative_to(root)}:\n" + "\n".join(excerpts)

    ocr = bool(match[1])
    if ocr:
        renderer = shutil.which("pdftoppm")
        executable = shutil.which("tesseract")
        installed = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe"
        if not executable and installed.is_file():
            executable = str(installed)
        if not renderer or not executable:
            raise ValueError("Para usar OCR, instala Poppler (pdftoppm) e Tesseract.")
    query = match[2].strip().strip('"').casefold()
    if not query:
        raise ValueError("Indica o texto a pesquisar.")
    results = []
    skipped = 0
    for folder, dirs, names in os.walk(root):
        parent = root.joinpath(folder)
        dirs[:] = sorted(name for name in dirs if name not in SKIP and
                         (parent / name).resolve().parent == parent)
        for name in sorted(names):
            path = parent / name
            if path.suffix.lower() != ".pdf" or path.resolve().parent != parent or path.is_symlink():
                continue
            try:
                with path.open("rb") as stream:
                    reader = PdfReader(stream)
                    for number, page in enumerate(reader.pages, 1):
                        raw = page.extract_text() or ""
                        if ocr and not raw.strip() and number <= 20:
                            raw = scan_page(path, number, renderer, executable)
                        body = " ".join(raw.split())
                        offset = body.casefold().find(query)
                        if offset >= 0:
                            excerpt = body[max(0, offset - 40):offset + len(query) + 60]
                            results.append(f"{path.relative_to(root)} · página {number}: {excerpt}")
                            if len(results) == 20:
                                return "\n".join(results)
            except (OSError, PdfReadError, ValueError, subprocess.SubprocessError):
                skipped += 1
    reply = "\n".join(results) if results else "Não encontrei a passagem no texto dos PDFs."
    if skipped:
        reply += f"\nPDFs indisponíveis: {skipped}."
    return reply


def scan_page(path, number, renderer, executable):
    with tempfile.TemporaryDirectory() as temporary:
        image = Path(temporary) / "page"
        subprocess.run(
            [renderer, "-f", str(number), "-l", str(number), "-r", "160", "-png",
             "-singlefile", str(path), str(image)],
            check=True, capture_output=True, timeout=20,
        )
        result = subprocess.run(
            [executable, str(image.with_suffix(".png")), "stdout"],
            check=True, capture_output=True, encoding="utf-8", timeout=20,
        )
        return result.stdout