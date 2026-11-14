"""Pesquisa de documentos PDF com referências por página."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .project_files import SKIP, safe_path

SEARCH = re.compile(r'procura (?:nos|em) pdfs?( com ocr)? (.+)', re.I)


def pdf_command(text, root, memory=None, sources=None):
    summary = re.fullmatch(r'resume (?:o )?pdf "([^"]+)"[.!]?', text, re.I)
    match = SEARCH.fullmatch(text)
    question = re.fullmatch(r"(?:responde com os pdfs|o que dizem os pdfs) sobre (.+)", text, re.I)
    if not match and not summary and not question:
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
        if sources is not None:
            sources.append((path.relative_to(root).as_posix(), None))
        return f"Resumo por excertos de {path.relative_to(root)}:\n" + "\n".join(excerpts)

    ocr = bool(match and match[1])
    ocr_options = []
    if ocr:
        renderer = shutil.which("pdftoppm")
        executable = shutil.which("tesseract")
        installed = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe"
        if not executable and installed.is_file():
            executable = str(installed)
        if not renderer or not executable:
            raise ValueError("Para usar OCR, instala Poppler (pdftoppm) e Tesseract.")
        language_dir = Path(os.environ.get("JARVIS_TESSDATA_DIR") or Path.home() / ".jarvis-portatil" / "ocr")
        if (language_dir / "por.traineddata").is_file():
            ocr_options = ["--tessdata-dir", str(language_dir), "-l", "por"]
    query = (question[1] if question else match[2]).strip().strip('"').casefold()
    if not query:
        raise ValueError("Indica o texto a pesquisar.")
    results = []
    skipped = 0
    indexed = {
        row["path"]: row for row in memory.execute("SELECT * FROM pdf_index WHERE ocr = ?", (ocr,))
    } if memory else {}
    seen = set()
    for folder, dirs, names in os.walk(root):
        parent = Path(folder)
        dirs[:] = sorted(name for name in dirs if name not in SKIP and
                         (parent / name).resolve().parent == parent)
        for name in sorted(names):
            path = parent / name
            if path.suffix.lower() != ".pdf" or path.resolve().parent != parent or path.is_symlink():
                continue
            key = str(path)
            seen.add(key)
            try:
                stat = path.stat()
                stamp = f"{stat.st_mtime_ns}:{stat.st_size}:{ocr_options}"
                cached = indexed.get(key)
                if cached and cached["stamp"] == stamp:
                    pages = json.loads(cached["pages"])
                else:
                    pages = []
                    with path.open("rb") as stream:
                        for number, page in enumerate(PdfReader(stream).pages, 1):
                            raw = page.extract_text() or ""
                            if ocr and not raw.strip() and number <= 20:
                                raw = scan_page(path, number, renderer, executable, ocr_options)
                            pages.append(" ".join(raw.split()))
                    if memory:
                        memory.execute(
                            """INSERT INTO pdf_index VALUES (?, ?, ?, ?)
                            ON CONFLICT(path, ocr) DO UPDATE SET stamp=excluded.stamp, pages=excluded.pages""",
                            (key, ocr, stamp, json.dumps(pages, ensure_ascii=False)),
                        )
                for number, body in enumerate(pages, 1):
                    offset = body.casefold().find(query)
                    if offset >= 0 and len(results) < 20:
                        excerpt = body[max(0, offset - 40):offset + len(query) + 60]
                        results.append(f"{path.relative_to(root)} · página {number}: {excerpt}")
                        if sources is not None:
                            sources.append((path.relative_to(root).as_posix(), number))
            except (OSError, PdfReadError, ValueError, subprocess.SubprocessError):
                skipped += 1
                if memory:
                    memory.execute("DELETE FROM pdf_index WHERE path = ? AND ocr = ?", (key, ocr))
    for key in indexed.keys() - seen:
        if Path(key).is_relative_to(root):
            memory.execute("DELETE FROM pdf_index WHERE path = ? AND ocr = ?", (key, ocr))
    reply = "\n".join(results) if results else "Não encontrei a passagem no texto dos PDFs."
    if question and results:
        reply = "Estas passagens dos PDFs respondem à pesquisa:\n" + reply
    if skipped:
        reply += f"\nPDFs indisponíveis: {skipped}."
    return reply


def scan_page(path, number, renderer, executable, ocr_options):
    with tempfile.TemporaryDirectory() as temporary:
        image = Path(temporary) / "page"
        subprocess.run(
            [renderer, "-f", str(number), "-l", str(number), "-r", "160", "-png",
             "-singlefile", str(path), str(image)],
            check=True, capture_output=True, timeout=20,
        )
        result = subprocess.run(
            [executable, str(image.with_suffix(".png")), "stdout", *ocr_options],
            check=True, capture_output=True, encoding="utf-8", timeout=20,
        )
        return result.stdout