"""Extract a bounded text preview from documents dropped into Quick Chat."""
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from .integrations.compare import attachment_sections

MAX_UPLOAD = 8 * 1024 * 1024
MAX_EXCERPT = 4500


def document_excerpt(content, suffix):
    if suffix not in {".pdf", ".docx"}:
        raise ValueError("Escolhe um PDF ou DOCX.")
    stream = BytesIO(content)
    if suffix == ".docx":
        try:
            with ZipFile(stream) as archive:
                entries = archive.infolist()
                if len(entries) > 1000 or sum(entry.file_size for entry in entries) > 24 * 1024 * 1024:
                    raise ValueError("O DOCX é demasiado grande depois de descomprimido.")
        except BadZipFile as error:
            raise ValueError("O DOCX está danificado.") from error
        stream.seek(0)
    sections = attachment_sections(stream, suffix)
    text = "\n".join(section for section in sections if section.strip()).strip()
    if not text:
        raise ValueError("O documento não contém texto.")
    return {"contents": text[:MAX_EXCERPT], "truncated": len(text) > MAX_EXCERPT}
