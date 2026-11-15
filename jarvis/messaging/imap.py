"""Importar mensagens de contas IMAP configuradas para o perfil local."""
import hashlib
import imaplib
import json
import os
import re
import ssl
import time
from pathlib import Path
from email.errors import MessageError
from urllib.parse import urlencode

from jarvis.integrations.editor import normalize
from jarvis.integrations.mail_draft import address_list
from jarvis.messaging.local_mail import MAX_FILE, draft_from_message, message_preview, parse_mail_content

ACCOUNT = r'([a-z0-9_-]{1,40})'
IMPORT = re.compile(rf'importa emails da conta "{ACCOUNT}"(?: da pasta "([^"\r\n]{{1,120}})")?(?: até (\d{{1,2}}))?[.!]?', re.I)
SEARCH = re.compile(rf'(?:procura|pesquisa) emails da conta "{ACCOUNT}" por (contacto|assunto|conteúdo) "([^"\r\n]{{1,180}})"[.!]?', re.I)
LIST = re.compile(r'(?:mostra|lista) as contas de email[.!]?', re.I)
ACCOUNT_ID = re.compile(r"[a-z0-9_-]{1,40}")
ACCOUNT_SECRET = re.compile(r"JARVIS_IMAP_[A-Z0-9_]{1,60}")
HOST = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?")
COUNT_LIMIT = 20
BATCH_BYTES = 20 * 1024 * 1024
REPLY = re.compile(
    rf'prepara (?:uma )?resposta à mensagem (\d{{1,18}}) da conta "{ACCOUNT}"(?: com "([^"]{{1,4000}})")?[.!]?',
    re.I,
)


class MailConnectionError(RuntimeError):
    pass


def configured_accounts(profile):
    filename = os.environ.get("JARVIS_IMAP_ACCOUNTS_FILE")
    if not filename:
        return {}
    path = Path(filename).expanduser()
    try:
        with path.open("rb") as stream:
            content = stream.read(64_001)
        if len(content) > 64_000:
            raise ValueError
        config = json.loads(content.decode("utf-8-sig"))
        profiles = config["perfis"]
        entries = profiles.get(profile, [])
        if not isinstance(entries, list) or len(entries) > 12:
            raise ValueError
        accounts = {}
        for entry in entries:
            account = validate_account(entry)
            if account["id"] in accounts:
                raise ValueError
            accounts[account["id"]] = account
        return accounts
    except (OSError, TypeError, AttributeError, KeyError, ValueError) as error:
        raise ValueError("Revê o ficheiro de contas IMAP, incluindo a configuração deste perfil.") from error


def validate_account(entry):
    identifier = entry["id"].casefold()
    host = entry["host"]
    username = entry["utilizador"]
    secret = entry["segredo_env"]
    folders = entry["pastas"]
    port = entry.get("porta", 993)
    auth = entry.get("autenticacao", "password")
    if (not ACCOUNT_ID.fullmatch(identifier) or not HOST.fullmatch(host) or not ACCOUNT_SECRET.fullmatch(secret)
            or not isinstance(username, str) or not 1 <= len(username) <= 320
            or any(ord(char) < 32 or ord(char) > 126 for char in username)
            or type(port) is not int or not 1 <= port <= 65535
            or auth not in {"password", "xoauth2"}
            or not isinstance(folders, list) or not 1 <= len(folders) <= 12
            or not all(isinstance(folder, str) and 1 <= len(folder) <= 120 and folder.isascii()
                       and all(32 <= ord(char) <= 126 for char in folder) for folder in folders)):
        raise ValueError
    identity = hashlib.sha256(f"{host.casefold()}\0{port}\0{username}".encode()).hexdigest()
    sent = entry.get("enviados")
    if sent is not None and sent not in folders:
        raise ValueError
    smtp = validate_smtp(entry["smtp"], username, secret, auth) if "smtp" in entry else None
    drafts = entry.get("rascunhos")
    if drafts is not None and drafts not in folders:
        raise ValueError
    webmail = entry.get("webmail")
    if webmail is not None and (not isinstance(webmail, str) or not 0 < len(webmail) <= 1500
                                or not webmail.startswith("https://")
                                or re.search(r"[{}]", re.sub(r"\{(?:uid|pasta|message_id)\}", "", webmail))):
        raise ValueError
    return {"id": identifier, "host": host, "port": port, "username": username, "secret": secret,
            "folders": list(dict.fromkeys(folders)), "auth": auth, "identity": identity, "sent": sent, "smtp": smtp,
            "drafts": drafts, "webmail": webmail}


def validate_smtp(entry, default_username, default_secret, default_auth):
    host = entry["host"]
    mode = entry.get("tls", "starttls")
    port = entry.get("porta", 465 if mode == "ssl" else 587)
    username = entry.get("utilizador", default_username)
    secret = entry.get("segredo_env", default_secret)
    auth = entry.get("autenticacao", default_auth)
    sender = address_list(entry.get("remetente", username))
    if (not HOST.fullmatch(host) or mode not in {"ssl", "starttls"} or type(port) is not int or not 1 <= port <= 65535
            or not ACCOUNT_SECRET.fullmatch(secret) or auth not in {"password", "xoauth2"} or len(sender) != 1
            or not isinstance(username, str) or not 1 <= len(username) <= 320
            or any(not 32 <= ord(char) <= 126 for char in username)):
        raise ValueError
    settings = {"host": host, "port": port, "mode": mode, "username": username, "secret": secret,
                "auth": auth, "sender": sender[0].addr_spec}
    settings["identity"] = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    return settings


def require_account(memory, identifier):
    account = configured_accounts(memory.path.stem).get(identifier.casefold())
    if not account:
        raise ValueError("Essa conta de email não está autorizada neste perfil.")
    return account


def imap_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def folder_for(account, name):
    names = account["folders"]
    if name is None:
        return names[0]
    if name in names:
        return name
    raise ValueError("Essa pasta não está autorizada para a conta.")


def secret_for(account):
    secret = os.environ.get(account["secret"], "")
    if not secret:
        raise ValueError("Configura a credencial IMAP no ambiente do JARVIS e reinicia a aplicação.")
    if not 1 <= len(secret) <= 8192 or any(not 32 <= ord(char) <= 126 for char in secret):
        raise ValueError("A credencial IMAP necessita de um valor ASCII válido para este método de autenticação.")
    return secret


def authenticate(client, account, secret):
    username = account["username"]
    if account["auth"] == "xoauth2":
        initial = f"user={username}\x01auth=Bearer {secret}\x01\x01".encode("ascii")
        client.authenticate("XOAUTH2", lambda challenge: b"" if challenge else initial)
    else:
        client.login(imap_string(username), secret)


def selected_messages(client, folder, count):
    status, sizes = client.select(imap_string(folder), readonly=True)
    if status != "OK" or not sizes[0] or not sizes[0].isdigit():
        raise MailConnectionError("A pasta IMAP recusou a leitura.")
    available = int(sizes[0])
    if not available:
        return None, []
    _, result = client.response("UIDVALIDITY")
    if not result or not result[0] or not result[0].isdigit():
        raise MailConnectionError("O serviço não identificou a versão da pasta IMAP.")
    generation = int(result[0])
    status, rows = client.fetch(f"{max(1, available - count + 1)}:{available}", "(UID RFC822.SIZE)")
    if status != "OK":
        raise MailConnectionError("Não consegui consultar as mensagens recentes da pasta.")
    metadata = {}
    for row in rows:
        if not isinstance(row, bytes):
            continue
        uid = re.search(rb"\bUID (\d{1,10})\b", row, re.I)
        size = re.search(rb"\bRFC822\.SIZE (\d+)\b", row, re.I)
        if uid and size and len(size[1]) < 12:
            metadata[int(uid[1])] = int(size[1])
    return generation, sorted(metadata.items(), reverse=True)[:count]


def fetch_message(client, uid, size):
    status, rows = client.uid("FETCH", str(uid), f"(UID BODY.PEEK[]<0.{size}>)")
    if status != "OK":
        return None
    for index, row in enumerate(rows):
        if isinstance(row, tuple) and len(row) == 2:
            header, literal = row
            remainder = rows[index + 1] if index + 1 < len(rows) else None
            if not isinstance(header, bytes) or not isinstance(literal, bytes) or len(literal) != size:
                continue
            if not re.search(rb"\bUID ", header, re.I) and isinstance(remainder, bytes):
                header += b" " + remainder
            if re.search(rb"\bUID " + str(uid).encode() + rb"\b", header, re.I):
                return literal
    return None


def fetch_mailbox(account, folder, count):
    secret = secret_for(account)
    available_bytes = BATCH_BYTES
    deadline = time.monotonic() + 20
    fetched, skipped = [], 0
    try:
        with imaplib.IMAP4_SSL(account["host"], account["port"], ssl_context=ssl.create_default_context(),
                              timeout=5) as client:
            authenticate(client, account, secret)
            generation, messages = selected_messages(client, folder, count)
            for uid, size in messages:
                if time.monotonic() >= deadline or not 0 < size <= min(MAX_FILE, available_bytes):
                    skipped += 1
                    continue
                content = fetch_message(client, uid, size)
                if content is None:
                    skipped += 1
                    continue
                available_bytes -= len(content)
                try:
                    preview = parse_mail_content(content, f"{folder} · UID {uid}")
                except (MessageError, ValueError, TypeError, AttributeError):
                    skipped += 1
                    continue
                fetched.append((uid, content, preview))
    except imaplib.IMAP4.error as error:
        raise MailConnectionError("O serviço IMAP recusou a autenticação ou a leitura da pasta.") from error
    except OSError as error:
        raise MailConnectionError("Não consegui estabelecer uma ligação IMAP segura.") from error
    return generation, fetched, skipped


def save_mail_batch(memory, account, folder, generation, fetched):
    current = require_account(memory, account["id"])
    if current["identity"] != account["identity"] or folder not in current["folders"]:
        raise ValueError("A autorização da conta ou da pasta mudou durante a importação.")
    saved = []
    for uid, content, message in fetched:
        contacts = " ".join(message[field] for field in ("from", "to", "cc"))
        row = memory.execute(
            """INSERT INTO imported_mail
               (account_id, identity, folder, generation, uid, body, subject, subject_key, contacts, search_body, dated, stamp, sender)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(account_id, identity, folder, generation, uid) DO NOTHING RETURNING id""",
            (account["id"], account["identity"], folder, generation, uid, content,
             message["subject"], normalize(message["subject"]), normalize(contacts), normalize(message["text"]),
             message["dated"].isoformat(timespec="minutes") if message["dated"] else None,
             message["dated"].timestamp() if message["dated"] else None, message["from"]),
        )
        original = not row
        if original:
            row = memory.execute(
                """SELECT id FROM imported_mail WHERE account_id=? AND identity=? AND folder=? AND generation=? AND uid=?""",
                (account["id"], account["identity"], folder, generation, uid),
            )
        saved.append((row[0]["id"], original, message))
    return saved


def import_messages(memory, account, folder, count):
    generation, fetched, skipped = fetch_mailbox(account, folder, count)
    saved = save_mail_batch(memory, account, folder, generation, fetched)
    duplicates = sum(previous for _, previous, _ in saved)
    reply = f"{account['id']} · {folder}\\n{len(saved) - duplicates} mensagem(ns) nova(s) e {duplicates} já importada(s)."
    if skipped:
        reply += f"\\n{skipped} ignorada(s) por tamanho, tempo ou erro de leitura."
    return {"reply": reply, "links": [], "transient": True}


def search_messages(memory, account, field, term):
    query = normalize(term.strip())
    if not query:
        raise ValueError("Indica um termo de pesquisa.")
    column = {"assunto": "subject_key", "contacto": "contacts", "conteudo": "search_body"}[normalize(field)]
    folders = ",".join("?" for _ in account["folders"])
    rows = memory.execute(
        f"""SELECT id, uid, folder, subject, sender, dated FROM imported_mail WHERE account_id=? AND identity=?
            AND folder IN ({folders}) AND instr({column}, ?) > 0 ORDER BY stamp DESC, id DESC LIMIT 16""",
        (account["id"], account["identity"], *account["folders"], query),
    )
    if not rows:
        return {"reply": "Não encontrei mensagens importadas para essa pesquisa.", "links": []}
    lines, links = [f"Mensagens importadas da conta {account['id']}"], []
    for row in rows[:15]:
        lines.append(f"Mensagem {row['id']} · {row['subject']} · {row['sender']} · {row['dated'] or 'sem data'} · {row['folder']}")
        links.append(imported_link(account["id"], row["id"], row["subject"]))
    if len(rows) > 15:
        lines.append("São apresentadas as 15 correspondências mais recentes.")
    return {"reply": "\n".join(lines), "links": links, "transient": True}


def imported_link(identifier, row_id, label):
    return {"label": label, "url": "/email-conta?" + urlencode({"conta": identifier, "id": row_id})}


def imported_record(memory, identifier, row_id):
    account = require_account(memory, identifier)
    if not re.fullmatch(r"\d{1,18}", row_id):
        raise ValueError("Identificador de mensagem inválido.")
    rows = memory.execute("SELECT folder, body FROM imported_mail WHERE id=? AND account_id=? AND identity=?",
                          (int(row_id), account["id"], account["identity"]))
    if not rows or rows[0]["folder"] not in account["folders"]:
        raise ValueError("Essa mensagem não está disponível neste perfil.")
    row = rows[0]
    return parse_mail_content(row["body"], row["folder"])


def imported_message(memory, identifier, row_id):
    return message_preview(imported_record(memory, identifier, row_id))


def account_reply_input(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    match = REPLY.fullmatch(command)
    if not match:
        return None
    account = require_account(memory, match[2])
    message = imported_record(memory, match[2], match[1])
    draft = draft_from_message(message, match[3])
    draft["account_source"] = {"account": account["id"], "id": match[1],
                               "identity": account["identity"], "folder": message["path"]}
    return draft


def account_draft_allowed(memory, draft):
    source = draft.get("account_source")
    if not source:
        return True
    try:
        account = require_account(memory, source["account"])
    except (ValueError, KeyError):
        return False
    return account["identity"] == source.get("identity") and source.get("folder") in account["folders"]


def account_mail_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if LIST.fullmatch(command):
        accounts = configured_accounts(memory.path.stem)
        lines = [f"{account['id']} · {', '.join(account['folders'])}" for account in accounts.values()]
        return {"reply": "\n".join(lines) or "Este perfil ainda não tem contas IMAP autorizadas.", "links": []}
    if match := IMPORT.fullmatch(command):
        account = require_account(memory, match[1])
        folder = folder_for(account, match[2])
        limit = int(match[3] or 10)
        if not 1 <= limit <= COUNT_LIMIT:
            raise ValueError(f"Indica um limite de 1 a {COUNT_LIMIT} mensagens.")
        return import_messages(memory, account, folder, limit)
    if match := SEARCH.fullmatch(command):
        return search_messages(memory, require_account(memory, match[1]), match[2], match[3])
    return None
