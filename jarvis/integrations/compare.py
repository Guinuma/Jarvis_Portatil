"""Comparação local de documentos com referências à origem."""
from difflib import SequenceMatcher
from pathlib import Path

from .project_files import safe_path

MAX_FILE = 32 * 1024 * 1024


def document_sections(path):
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError("Indica um documento existente com até 32 MB.")
    suffix = path.suffix.lower()
    if suffix in {".pdf", ".docx"}:
        with path.open("rb") as stream:
            return attachment_sections(stream, suffix)
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8-sig").splitlines()
    raise ValueError("Escolhe dois documentos PDF, DOCX, TXT ou Markdown do mesmo formato.")


def attachment_sections(stream, suffix):
    if suffix == ".docx":
        from .office import office_module

        document = office_module(".docx")(stream)
        return [paragraph.text for paragraph in document.paragraphs]
    try:
        from pypdf import PdfReader
        from pypdf.errors import PyPdfError
    except ImportError as error:
        raise ValueError("Instala pypdf para ler PDFs.") from error
    try:
        pages = PdfReader(stream).pages
        if len(pages) > 100:
            raise ValueError("São suportados PDFs com até 100 páginas.")
        sections = [" ".join((page.extract_text() or "").split()) for page in pages]
    except PyPdfError as error:
        raise ValueError("Não consegui extrair o texto do PDF.") from error
    if not any(sections):
        raise ValueError("O PDF não contém texto selecionável. Prepara uma versão com OCR.")
    return sections


def compare_documents(root, old_name, new_name):
    old, new = [safe_path(root, name) for name in (old_name, new_name)]
    suffix = old.suffix.lower()
    if old == new or suffix != new.suffix.lower():
        raise ValueError("Escolhe dois documentos diferentes do mesmo formato.")
    before, after = document_sections(old), document_sections(new)
    if max(len(before), len(after)) > 5000 or sum(map(len, before + after)) > 500_000:
        raise ValueError("Os documentos excedem o limite de texto da comparação.")
    changes = []
    for change in section_changes(before, after, suffix == ".pdf"):
        if len(changes) == 30:
            omitted = True
            break
        changes.append(change)
    else:
        omitted = False
    return {
        "old": old.relative_to(root).as_posix(), "new": new.relative_to(root).as_posix(),
        "unit": {".pdf": "página", ".docx": "parágrafo"}.get(suffix, "linha"),
        "changes": changes, "omitted": omitted,
    }


def section_changes(before, after, pdf):
    for operation, i, j, k, l in SequenceMatcher(None, before, after).get_opcodes():
        if operation == "equal":
            continue
        for index in range(max(j - i, l - k)):
            left = i + index if i + index < j else None
            right = k + index if k + index < l else None
            removed = before[left] if left is not None else ""
            added = after[right] if right is not None else ""
            snippets = word_changes(removed, added) if pdf and removed and added else [(removed, added)]
            for old_text, new_text in snippets:
                yield {
                    "old": left + 1 if left is not None else None,
                    "new": right + 1 if right is not None else None,
                    "removed": excerpt(old_text),
                    "added": excerpt(new_text),
                }


def word_changes(removed, added):
    before, after = removed.split(), added.split()
    for operation, i, j, k, l in SequenceMatcher(None, before, after).get_opcodes():
        if operation != "equal":
            yield (" ".join(before[max(i - 4, 0):j + 4]), " ".join(after[max(k - 4, 0):l + 4]))


def excerpt(text):
    return text[:240] + ("…" if len(text) > 240 else "")


def comparison_text(result):
    lines = [f"Versão anterior — {result['old']}", f"Versão atual — {result['new']}"]
    for change in result["changes"]:
        for side, field, label in (("old", "removed", "Antes"), ("new", "added", "Agora")):
            if change[side] is not None:
                lines.append(f"{label} ({result['unit']} {change[side]}) — {change[field]}")
    if not result["changes"]:
        lines.append("O texto extraído é igual nas duas versões.")
    if result["omitted"]:
        lines.append("São apresentadas as primeiras 30 diferenças.")
    return "\n".join(lines)


def comparison_sources(result):
    if Path(result["old"]).suffix.lower() != ".pdf":
        return []
    return list(dict.fromkeys(
        (result[side], change[side])
        for change in result["changes"]
        for side in ("old", "new")
        if change[side] is not None
    )) or [(result["old"], None), (result["new"], None)]
