"""Extrair tabelas de um PDF para CSV sem substituir ficheiros."""
import csv
import os
import re
import tempfile
from pathlib import Path

from .compare import MAX_FILE
from .project_files import safe_path

COMMAND = re.compile(
    r'extrai (?:a )?tabela (\d{1,3}) da página (\d{1,4}) de "([^"]+)" para "([^"]+)"[.!]?', re.I
)


def table_command(text, root, sources):
    match = COMMAND.fullmatch(text)
    if not match:
        return None
    table, page = map(int, match.groups()[:2])
    source, target = [safe_path(root, name) for name in match.groups()[2:]]
    if not page or not table or source.suffix.lower() != ".pdf" or target.suffix.lower() != ".csv":
        raise ValueError("Indica a página e a tabela a partir de 1, um PDF e um destino CSV.")
    if not source.is_file() or source.stat().st_size > MAX_FILE:
        raise ValueError("Indica um PDF existente com até 32 MB.")
    try:
        import pdfplumber
        from pdfplumber.utils.exceptions import MalformedPDFException, PdfminerException
        from pdfminer.psparser import PSException
    except ImportError as error:
        raise ValueError("Instala pdfplumber para extrair tabelas de PDFs.") from error
    try:
        with pdfplumber.open(source) as document:
            if page > len(document.pages):
                raise ValueError("A página indicada não existe.")
            tables = document.pages[page - 1].extract_tables()
    except (MalformedPDFException, PdfminerException, PSException) as error:
        raise ValueError("Não consegui interpretar a página do PDF.") from error
    if table > len(tables) or not tables[table - 1]:
        raise ValueError(f"Encontrei {len(tables)} tabelas na página indicada.")
    rows = [[csv_value(value or "") for value in row] for row in tables[table - 1]]
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", dir=target.parent,
                                     suffix=".csv", delete=False) as temporary:
        output = Path(temporary.name)
        try:
            csv.writer(temporary, delimiter=";").writerows(rows)
            temporary.close()
            with output.open(encoding="utf-8-sig", newline="") as stream:
                if list(csv.reader(stream, delimiter=";")) != rows:
                    raise ValueError("A tabela relida diverge da grelha extraída.")
            os.link(output, target)
        finally:
            temporary.close()
            output.unlink(missing_ok=True)
    sources.append((source.relative_to(root).as_posix(), page))
    return f"Tabela {table}, página {page}: {len(rows)} linhas em {target.relative_to(root)}."


def csv_value(value):
    # Keep signed numbers as numbers and neutralize formula-like cells from the PDF.
    if re.fullmatch(r"[+-]?[0-9]+(?:[.,][0-9]+)?", value.strip()):
        return value
    if value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
