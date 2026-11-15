"""Preparar anexos autorizados e exportar o rascunho revisto em formato EML."""
import hashlib
import mimetypes
from email import policy
from email.errors import HeaderParseError
from email.headerregistry import Address
from email.message import EmailMessage

from .project_files import SKIP, safe_path

MAX_TOTAL = 10 * 1024 * 1024
MAX_FILES = 5


def read_attachment(root, name, remaining):
    if not isinstance(name, str) or not 1 <= len(name) <= 500 or any(c in name for c in '\r\n\x00:"'):
        raise ValueError("Indica um caminho relativo válido para cada anexo.")
    path = safe_path(root, name)
    relative = path.relative_to(root)
    if any(part.startswith(".") or part in SKIP for part in relative.parts) or not path.is_file():
        raise ValueError(f"Anexo indisponível no projeto: {name}.")
    if path.stat().st_size > remaining:
        raise ValueError("Os anexos excedem 10 MB no total.")
    with path.open("rb") as stream:
        content = stream.read(remaining + 1)
    if len(content) > remaining:
        raise ValueError("Os anexos excedem 10 MB no total.")
    metadata = {"path": relative.as_posix(), "name": path.name, "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest()}
    return metadata, content


def review_attachments(root, names):
    if not isinstance(names, list) or len(names) > MAX_FILES:
        raise ValueError(f"Indica até {MAX_FILES} anexos, um caminho por linha.")
    seen, reviewed = set(), []
    remaining = MAX_TOTAL
    for name in names:
        metadata, content = read_attachment(root, name, remaining)
        if metadata["path"] in seen:
            raise ValueError("Remove os anexos repetidos da lista.")
        seen.add(metadata["path"])
        reviewed.append(metadata)
        remaining -= len(content)
    return reviewed


def address_list(value):
    if not value.strip():
        return ()
    try:
        addresses = tuple(Address(addr_spec=part.strip()) for part in value.split(","))
        if any(not address.username or not address.domain for address in addresses):
            raise ValueError
    except (ValueError, HeaderParseError, IndexError) as error:
        raise ValueError("Usa endereços de email completos separados por vírgulas para exportar o EML.") from error
    return addresses


def build_draft(root, draft, attachments, thread=None):
    message = EmailMessage(policy=policy.SMTP)
    addresses = address_list(draft["recipient"])
    if addresses:
        message["To"] = addresses
    message["Subject"] = draft["subject"]
    if thread:
        if thread["reply_to"]:
            message["In-Reply-To"] = thread["reply_to"]
        if thread["references"]:
            message["References"] = " ".join(thread["references"])
    message.set_content(draft["body"])
    remaining = MAX_TOTAL
    for expected in attachments:
        try:
            current, content = read_attachment(root, expected["path"], remaining)
        except (OSError, ValueError, RuntimeError) as error:
            raise ValueError(f"Revê e guarda novamente o anexo {expected['name']}.") from error
        if current != expected:
            raise ValueError(f"O anexo {expected['name']} mudou desde a revisão. Guarda e revê a nova versão.")
        mime_type = mimetypes.guess_type(current["name"])[0] or "application/octet-stream"
        main, subtype = mime_type.split("/", 1)
        message.add_attachment(content, maintype=main, subtype=subtype, filename=current["name"])
        remaining -= len(content)
    return message


def export_draft(root, draft, attachments, thread=None):
    return build_draft(root, draft, attachments, thread).as_bytes()
