"""Pesquisar mensagens e reconstruir conversas numa pasta IMAP autorizada."""
import imaplib
import re
import ssl
import time
from urllib.parse import quote

from jarvis.messaging.imap import (
    BATCH_BYTES, MAX_FILE, MailConnectionError, authenticate, fetch_message, folder_for,
    imap_string, imported_link, imported_record, require_account, save_mail_batch, secret_for,
)
from jarvis.integrations.editor import normalize
from jarvis.messaging.local_mail import body_excerpt, message_line, parse_mail_content, review_thread, thread_for
from jarvis.integrations.http_client import public_link
from jarvis.education.reasoning import LocalModelError, ask_local, records_schema

ACCOUNT = r'"([a-z0-9_-]{1,40})"'
SEARCH = re.compile(
    rf'(?:procura|pesquisa) diretamente emails da conta {ACCOUNT}(?: na pasta "([^"\r\n]{{1,120}})")?'
    r' por (contacto|assunto|conteúdo) "([^"\r\n]{1,180})"[.!]?', re.I,
)
REVIEW = re.compile(
    rf'(resume|extrai tarefas|extrai datas|identifica perguntas pendentes) '
    rf'(?:a |da )?conversa online da mensagem (\d{{1,18}}) da conta {ACCOUNT}[.!]?', re.I,
)
FORMAT_FIELDS = re.compile(r"\{(uid|pasta|message_id)\}")


def online_mail_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := SEARCH.fullmatch(command):
        account = require_account(memory, match[1])
        folder = folder_for(account, match[2])
        term = match[4].strip()
        if not term or any(ord(char) < 32 for char in term):
            raise ValueError("Indica um termo de pesquisa sem quebras de linha.")
        literal = imap_string(term).encode("utf-8")
        field = normalize(match[3])
        criteria = {"assunto": ("SUBJECT", literal), "conteudo": ("BODY", literal),
                    "contacto": ("OR", "FROM", literal, "OR", "TO", literal, "CC", literal)}[field]
        if not term.isascii():
            criteria = ("CHARSET", "UTF-8", *criteria)
        saved, total, incomplete = query_folder(memory, account, folder, criteria)
        lines = [f"Pesquisa direta · {account['id']} · {folder} · {total} correspondência(s)"]
        lines.extend(f"Mensagem {identifier} · {message_line(message)}" for identifier, _, message in saved)
        if not saved:
            lines.append("O serviço não devolveu mensagens que pudessem ser abertas.")
        if incomplete or len(saved) < total:
            lines.append("A lista local mostra até 12 correspondências recentes em tamanho suportado.")
        return output("\n".join(lines), account, folder, saved)
    if match := REVIEW.fullmatch(command):
        return review_conversation(memory, match[3], match[2], match[1].casefold())
    return None


def query_folder(memory, account, folder, criteria):
    total_bytes = BATCH_BYTES
    deadline = time.monotonic() + 24
    fetched = []
    secret = secret_for(account)
    try:
        with imaplib.IMAP4_SSL(account["host"], account["port"], ssl_context=ssl.create_default_context(),
                              timeout=6) as client:
            authenticate(client, account, secret)
            status, _ = client.select(imap_string(folder), readonly=True)
            if status != "OK":
                raise MailConnectionError("O serviço recusou a leitura da pasta selecionada.")
            _, validity = client.response("UIDVALIDITY")
            if not validity or not validity[0] or not re.fullmatch(rb"\d{1,10}", validity[0]):
                raise MailConnectionError("O serviço não identificou a versão da pasta.")
            generation = int(validity[0])
            status, response = client.uid("SEARCH", *criteria)
            if status != "OK" or not response:
                raise MailConnectionError("O servidor recusou a pesquisa IMAP.")
            uids = sorted({int(item) for item in (response[0] or b"").split() if re.fullmatch(rb"\d{1,10}", item)}, reverse=True)
            for uid in uids[:12]:
                if time.monotonic() >= deadline or total_bytes <= 0:
                    break
                status, metadata = client.uid("FETCH", str(uid), "(RFC822.SIZE)")
                if status != "OK":
                    continue
                size = next((match for part in metadata if isinstance(part, bytes)
                             if (match := re.search(rb"\bRFC822\.SIZE (\d{1,10})\b", part))), None)
                if not size or not 0 < int(size[1]) <= min(MAX_FILE, total_bytes):
                    continue
                content = fetch_message(client, uid, int(size[1]))
                if not content:
                    continue
                total_bytes -= len(content)
                try:
                    message = parse_mail_content(content, f"uid:{uid}")
                except (ValueError, TypeError, AttributeError):
                    continue
                fetched.append((uid, content, message))
    except (imaplib.IMAP4.error, OSError) as error:
        raise MailConnectionError("A pesquisa IMAP direta falhou. Revê a credencial e o suporte à consulta no servidor.") from error
    by_path = {message["path"]: uid for uid, _, message in fetched}
    saved = [(identifier, by_path[message["path"]], message)
             for identifier, _, message in save_mail_batch(memory, account, folder, generation, fetched)]
    return saved, len(uids), len(saved) < len(uids)


def review_conversation(memory, identifier, row_id, action):
    account = require_account(memory, identifier)
    anchor = imported_record(memory, identifier, row_id)
    folder = folder_for(account, anchor["path"])
    anchor["path"] = f"message:{row_id}"
    ids = [identifier for identifier in (anchor["identifier"], *anchor["references"][:1]) if identifier]
    if not ids:
        raise ValueError("A origem não inclui referências de conversa para pesquisar no serviço.")
    ancestor = imap_string(ids[-1])
    criteria = ("OR", "HEADER", "Message-ID", ancestor, "OR", "HEADER", "References", ancestor,
                "HEADER", "In-Reply-To", ancestor)
    saved, _, incomplete = query_folder(memory, account, folder, criteria)
    candidates = [*saved, (int(row_id), None, anchor)]
    unique = {}
    for row in candidates:
        unique.setdefault(row[2]["identifier"] or row[2]["path"], row)
    candidates = list(unique.values())
    root = next(message for _, _, message in candidates if message["identifier"] == anchor["identifier"]
                or message["path"] == anchor["path"]) if anchor["identifier"] else anchor
    messages = thread_for(root, [message for _, _, message in candidates])
    by_path = {row[2]["path"]: row for row in candidates}
    if action.startswith("identifica"):
        reply = pending_questions(messages)
    else:
        reply = review_thread(messages, action)
    if incomplete:
        reply += "\nA consulta cobre as mensagens recentes que puderam ser lidas na pasta indicada."
    return output(reply, account, folder, [by_path[message["path"]] for message in messages])


def pending_questions(messages):
    snippets = [{"mensagem": index, "texto": " ".join(body_excerpt(message["text"]))[:900]}
                for index, message in enumerate(messages, 1)]
    schema = records_schema("perguntas", {"mensagem": {"type": "integer"}, "citação": {"type": "string"},
                                          "estado": {"type": "string", "enum": ["por responder", "incerta"]}})
    result = ask_local(
        "Considera a ordem da conversa. Lista só perguntas sem resposta clara nas mensagens seguintes. "
        "Para cada uma, copia o trecho literal da pergunta e indica se está por responder ou incerta.",
        snippets, limit=1000, schema=schema,
    )
    records = result.get("perguntas") if isinstance(result, dict) else None
    if not isinstance(records, list) or len(records) > 20:
        raise LocalModelError("Não consegui obter uma análise contextual válida.")
    lines = ["Perguntas possivelmente pendentes · análise orientativa"]
    for item in records:
        if not isinstance(item, dict):
            continue
        index, literal, state = item.get("mensagem"), item.get("citação"), item.get("estado")
        if (type(index) is int and 1 <= index <= len(snippets) and isinstance(literal, str)
                and state in ("por responder", "incerta")):
            literal = " ".join(literal.split())
            if literal and "?" in literal and len(literal) <= 300 and literal in snippets[index - 1]["texto"]:
                lines.append(f"[{index}] «{literal}» · {state}")
    if len(lines) == 1:
        lines.append("A análise não encontrou perguntas pendentes com um excerto verificável.")
    return "\n".join(lines)


def remote_link(account, folder, uid, message):
    template = account.get("webmail")
    if not template:
        return None
    values = {"pasta": folder, "uid": "" if uid is None else str(uid), "message_id": message["identifier"] or ""}
    missing = any(not values[field] for field in FORMAT_FIELDS.findall(template))
    if missing:
        return None
    url = FORMAT_FIELDS.sub(lambda match: quote(values[match[1]], safe=""), template)
    try:
        return public_link(url) if url.startswith("https://") else None
    except ValueError:
        return None


def output(reply, account, folder, saved):
    links = []
    for index, (identifier, uid, message) in enumerate(saved, 1):
        links.append(imported_link(account["id"], identifier, f"[{index}] {message['subject']}"))
        if url := remote_link(account, folder, uid, message):
            links.append({"label": f"[{index}] Abrir no serviço de email", "url": url})
    return {"reply": reply, "links": links, "transient": True}
