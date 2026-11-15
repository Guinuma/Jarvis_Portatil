"""Ler mensagens EML e consultar conversas locais sem contactar serviços externos."""
import os
import re
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from email import policy
from email.errors import MessageError
from email.parser import BytesParser
from pathlib import Path

from jarvis.integrations.editor import normalize
from jarvis.integrations.html_text import PlainHTML
from jarvis.integrations.project_files import SKIP, safe_path

MAIL_FOLDER = "emails"
MAX_FILE = 4 * 1024 * 1024
MAX_SCAN = 40 * 1024 * 1024
MAX_FILES = 300
MAX_BODY = 60_000
MAIL_ID = r"<[^\s<>@]+@[^\s<>@]+>"
MAIL_ID_PATTERN = re.compile(MAIL_ID)
SEARCH = re.compile(r'(?:procura|pesquisa) emails? por (contacto|assunto|conteúdo) "([^"\r\n]{1,180})"[.!]?', re.I)
REVIEW = re.compile(r'(resume|mostra as perguntas|extrai tarefas|extrai datas) (?:a|da) conversa "([^"\r\n]{1,500})"[.!]?', re.I)
REPLY = re.compile(r'prepara (?:uma )?resposta (?:ao|à mensagem) "([^"\r\n]{1,500})"(?: com "([^"]{1,4000})")?[.!]?', re.I)
TASK = re.compile(
    r"^(?:(?:tarefa|ação|action item|todo)\s*[:–-]|(?:por favor[, ]+)?"
    r"(?:podes|pode|podem|precisamos de|fico de|vou|confirma|envia|revê|entrega|trata de|please|could you|can you)\b)",
    re.I,
)
DATE = re.compile(
    r"(?<!\d)(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)(?!\d)"
    r"|\b(?:amanhã|hoje|depois de amanhã|(?:próxima |próximo )?(?:segunda|terça|quarta|quinta|sexta)(?:-feira)?"
    r"|(?:próximo )?sábado|(?:próximo )?domingo)\b",
    re.I,
)


def mail_path(root, name):
    inbox = safe_path(root, MAIL_FOLDER)
    if inbox == root or inbox != root / MAIL_FOLDER:
        raise ValueError("A pasta emails tem de estar diretamente no projeto.")
    path = safe_path(root, name)
    if (not path.is_relative_to(inbox) or path.suffix.lower() != ".eml"
            or any(part.startswith(".") or part in SKIP for part in path.relative_to(inbox).parts)
            or not path.is_file() or path.stat().st_size > MAX_FILE):
        raise ValueError("Indica um ficheiro EML da pasta emails com até 4 MB.")
    return path


def clean_header(message, field, limit=300):
    return " ".join(str(message.get(field, "")).split())[:limit]


def mail_ids(value):
    return [token for token in MAIL_ID_PATTERN.findall(value) if token.isascii() and len(token) <= 300]


def parse_mail(root, path):
    with path.open("rb") as stream:
        content = stream.read(MAX_FILE + 1)
    return parse_mail_content(content, path.relative_to(root).as_posix())


def parse_mail_content(content, source):
    if len(content) > MAX_FILE:
        raise ValueError("A mensagem excede 4 MB.")
    try:
        message = BytesParser(policy=policy.default).parsebytes(content)
    except (MessageError, ValueError) as error:
        raise ValueError("Não consegui interpretar a mensagem EML.") from error
    if not any(message.get(field) for field in ("From", "To", "Subject", "Message-ID")):
        raise ValueError("O ficheiro EML não tem cabeçalhos de mensagem reconhecíveis.")
    body = message.get_body(preferencelist=("plain", "html"))
    text = ""
    if body:
        try:
            text = body.get_content(errors="replace")
        except LookupError:
            text = (body.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        if body.get_content_subtype() == "html":
            parser = PlainHTML()
            parser.feed(text)
            parser.close()
            text = "".join(parser.parts)
    try:
        date_header = message["Date"]
        timestamp = date_header.datetime if date_header else None
        if timestamp and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, AttributeError):
        timestamp = None
    sender = message["Reply-To"] or message["From"]
    addresses = getattr(sender, "addresses", ())
    recipients = []
    for address in addresses:
        if address.username and address.domain and len(", ".join([*recipients, address.addr_spec])) <= 320:
            recipients.append(address.addr_spec)
    identifier = mail_ids(clean_header(message, "Message-ID"))
    references = mail_ids(clean_header(message, "References", 8000) + " " + clean_header(message, "In-Reply-To", 800))
    return {
        "path": source, "from": clean_header(message, "From"),
        "to": clean_header(message, "To"), "cc": clean_header(message, "Cc"),
        "subject": clean_header(message, "Subject") or "(sem assunto)",
        "dated": timestamp, "text": text[:MAX_BODY], "truncated": len(text) > MAX_BODY,
        "identifier": identifier[0] if identifier else None, "references": references, "recipients": recipients,
    }


def scan_mail(root):
    inbox = safe_path(root, MAIL_FOLDER)
    if inbox != root / MAIL_FOLDER or not inbox.is_dir():
        raise ValueError("Cria a pasta emails no projeto e coloca lá as mensagens EML.")
    scanned = total = skipped = 0
    records = []
    for folder, dirs, names in os.walk(inbox):
        parent = Path(folder)
        dirs[:] = sorted(name for name in dirs if name not in SKIP and not name.startswith(".")
                         and not (parent / name).is_symlink() and (parent / name).resolve().parent == parent)
        for name in sorted(names):
            path = parent / name
            if name.startswith(".") or path.suffix.lower() != ".eml" or path.is_symlink():
                continue
            if scanned == MAX_FILES:
                return records, skipped, True
            scanned += 1
            try:
                path = mail_path(root, path.relative_to(root).as_posix())
                size = path.stat().st_size
                if total + size > MAX_SCAN:
                    return records, skipped, True
                total += size
                record = parse_mail(root, path)
                records.append(record)
            except (OSError, ValueError, RuntimeError, MessageError):
                skipped += 1
    return records, skipped, False


def thread_for(selected, messages):
    refs = defaultdict(list)
    by_path = {message["path"]: message for message in messages}
    for message in by_path.values():
        for identifier in message["references"] + ([message["identifier"]] if message["identifier"] else []):
            refs[identifier].append(message["path"])
    targets, seen, identifiers = deque([selected["path"]]), {selected["path"]}, set()
    while targets:
        message = by_path[targets.popleft()]
        for identifier in message["references"] + ([message["identifier"]] if message["identifier"] else []):
            if identifier in identifiers:
                continue
            identifiers.add(identifier)
            for path in refs[identifier]:
                if path not in seen:
                    targets.append(path)
                    seen.add(path)
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    return sorted((by_path[path] for path in seen), key=lambda record: (record["dated"] or minimum, record["path"]))


def body_excerpt(text):
    lines = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if line in {"--", "-----Original Message-----", "-----Mensagem original-----"}:
            break
        if line and not line.startswith(">"):
            lines.append(line)
    return lines


def message_line(message):
    stamp = message["dated"].isoformat(timespec="minutes") if message["dated"] else "data indisponível"
    return f"{message['subject']} · {message['from'] or 'remetente indisponível'} · {stamp}"


def mail_view(root, name):
    return message_preview(parse_mail(root, mail_path(root, name)))


def message_preview(message):
    excerpt_notice = "\n\n[Mensagem limitada aos primeiros 60.000 caracteres de texto.]" if message["truncated"] else ""
    return f"{message_line(message)}\nPara: {message['to']}\nCc: {message['cc']}\n\n{message['text']}{excerpt_notice}"


def scan_note(skipped, limited):
    notes = []
    if skipped:
        notes.append(f"{skipped} ficheiro(s) ignorado(s) por formato, tamanho ou erro de leitura.")
    if limited:
        notes.append("A consulta atingiu o limite local de ficheiros ou de tamanho. Os resultados podem estar incompletos.")
    return "\n".join(notes)


def mail_search(root, field, query):
    query = normalize(query.strip())
    if not query:
        raise ValueError("Indica um termo de pesquisa.")
    records, skipped, limited = scan_mail(root)

    def matching(message):
        if field == "contacto":
            value = " ".join(message[key] for key in ("from", "to", "cc"))
        elif field == "assunto":
            value = message["subject"]
        else:
            value = message["text"]
        return query in normalize(value)

    minimum = datetime.min.replace(tzinfo=timezone.utc)
    matched = sorted(filter(matching, records), key=lambda record: record["dated"] or minimum, reverse=True)
    lines = [f"Encontrei {len(matched)} mensagem(ns) na pasta emails."]
    for index, message in enumerate(matched[:15], 1):
        lines.append(f"{index}. {message_line(message)} · {message['path']}")
    if len(matched) > 15:
        lines.append("A lista mostra as 15 mensagens mais recentes.")
    return "\n".join(filter(None, [*lines, scan_note(skipped, limited)])), [message["path"] for message in matched[:15]]


def describe_date(value):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return "dia inválido. Confirma a data por extenso"
        return parsed.isoformat()
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", value):
        day, month, year = map(int, re.split(r"[/-]", value))
        if 1 <= day <= 12 and 1 <= month <= 12 and day != month:
            return "ordem dia/mês ambígua. Confirma a data por extenso"
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return "dia ou mês inválido. Confirma a data por extenso"
    return "confirma o dia exato no formato AAAA-MM-DD"


def review_thread(messages, action):
    lines = []
    for index, message in enumerate(messages, 1):
        body = body_excerpt(message["text"])
        if action == "resume":
            summary = " ".join(body[:3])
            lines.append(f"[{index}] {message_line(message)}\n{summary[:400] or '(sem texto no corpo)'}")
            continue
        for line in body:
            if action == "mostra as perguntas" and "?" in line:
                label = "mensagem mais recente" if index == len(messages) else "resposta por confirmar"
                lines.append(f"[{index}] {line[:230]} · {label}")
            if action == "extrai tarefas" and TASK.search(line):
                lines.append(f"[{index}] {line[:230]}")
            if action == "extrai datas":
                for found in DATE.finditer(line):
                    value = found.group()
                    lines.append(f"[{index}] {value} · {describe_date(value)} · {line[:150]}")
            if len(lines) >= 30:
                break
        if len(lines) >= 30:
            break
    headings = {"resume": "Resumo por excertos", "mostra as perguntas": "Perguntas candidatas a seguimento",
                "extrai tarefas": "Pedidos e compromissos candidatos", "extrai datas": "Datas mencionadas"}
    if not lines:
        lines.append("Não encontrei correspondências no texto das mensagens.")
    if len(lines) > 30:
        lines = lines[:30]
    if len(lines) == 30:
        lines.append("A lista foi limitada às primeiras 30 ocorrências.")
    return headings[action] + "\n" + "\n\n".join(lines)


def mail_command(text, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := SEARCH.fullmatch(command):
        result, sources = mail_search(root, normalize(match[1]), match[2])
        return {"reply": result, "mail_sources": sources}
    if match := REVIEW.fullmatch(command):
        selected = parse_mail(root, mail_path(root, match[2]))
        records, skipped, limited = scan_mail(root)
        messages = thread_for(selected, [*records, selected])
        last = len(messages)
        messages = messages[-15:]
        reply = review_thread(messages, match[1].casefold())
        if last > len(messages):
            reply += "\nA análise cobre as últimas 15 mensagens encontradas na conversa."
        if note := scan_note(skipped, limited):
            reply += "\n" + note
        return {"reply": reply, "mail_sources": [message["path"] for message in messages]}
    return None


def reply_input(text, root):
    match = REPLY.fullmatch(re.sub(r"^jarvis,\s*", "", text, flags=re.I))
    if not match:
        return None
    message = parse_mail(root, mail_path(root, match[1]))
    draft = draft_from_message(message, match[2])
    draft["mail_sources"] = [message["path"]]
    return draft


def draft_from_message(message, text):
    subject = message["subject"]
    if not subject.casefold().startswith("re:"):
        subject = "Re: " + subject
    reply = (text or "").strip()
    body = f"Olá,\n\n{reply}\n\nCumprimentos" if reply else "Olá,\n\n[Escreve aqui a resposta.]\n\nCumprimentos"
    reference = message["identifier"]
    references = [*message["references"], *([reference] if reference else [])]
    return {
        "kind": "mail_reply",
        "draft": {"recipient": ", ".join(message["recipients"]), "subject": subject[:300], "body": body},
        "thread": {"reply_to": reference, "references": list(dict.fromkeys(references))[-12:]},
    }
