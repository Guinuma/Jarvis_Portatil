"""Ler e enviar texto em salas Matrix explicitamente autorizadas."""
import hashlib
import json
import os
import re
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, build_opener
from uuid import uuid4

from jarvis.integrations.http_client import NoRedirect, ServiceError, public_link

LABEL = r'"([a-zA-Z0-9_-]{1,40})"'
OPEN = re.compile(rf'abre (?:a )?sala matrix {LABEL}[.!]?', re.I)
LIST = re.compile(r'mostra (?:as )?salas matrix[.!]?', re.I)
READ = re.compile(rf'(?:mostra|procura) mensagens matrix em {LABEL}(?: com "([^"\r\n]{{1,160}})")?[.!]?', re.I)
PREPARE = re.compile(rf'prepara mensagem matrix para {LABEL} com "(.{{1,4000}})"[.!]?', re.I | re.S)
CONFIRM = re.compile(r'confirma (?:a )?mensagem matrix (\d{1,18}) com ([a-f0-9]{8})[.!]?', re.I)
CANCEL = re.compile(r'cancela (?:a )?mensagem matrix (\d{1,18})[.!]?', re.I)
STATUS = re.compile(r'(?:mostra|verifica) (?:a )?mensagem matrix (\d{1,18})[.!]?', re.I)


class MatrixHTTP(ServiceError):
    def __init__(self, status, code):
        super().__init__(f"O Matrix devolveu HTTP {status}.")
        self.status = status
        self.code = code


def rooms(memory):
    filename = os.environ.get("JARVIS_MATRIX_ROOMS_FILE")
    if not filename:
        return {}
    try:
        with Path(filename).expanduser().open("rb") as stream:
            content = stream.read(64_001)
        if len(content) > 64_000:
            raise ValueError
        configured = json.loads(content.decode("utf-8-sig"))["perfis"].get(memory.path.stem, [])
        if not isinstance(configured, list) or len(configured) > 16:
            raise ValueError
        found = {}
        for item in configured:
            label, server, room, token = [item[key] for key in ("id", "servidor", "sala", "token_env")]
            label = label.casefold()
            parsed = urlsplit(public_link(server))
            if (not re.fullmatch(r"[a-z0-9_-]{1,40}", label) or label in found
                    or parsed.scheme != "https" or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
                    or not re.fullmatch(r"![^ \x00-\x1f/]{1,200}", room)
                    or not re.fullmatch(r"JARVIS_MATRIX_[A-Z0-9_]{1,50}", token)
                    or type(item.get("enviar", False)) is not bool):
                raise ValueError
            found[label] = {"label": label, "server": server.rstrip("/"), "room": room, "token": token,
                            "write": item.get("enviar", False)}
        return found
    except (OSError, TypeError, AttributeError, ValueError, KeyError) as error:
        raise ValueError("Revê o ficheiro de salas Matrix para este perfil.") from error


def require_room(memory, label, writing=False):
    room = rooms(memory).get(label.casefold())
    if not room or (writing and not room["write"]):
        raise ValueError("Essa sala Matrix não está autorizada para esta ação no perfil atual.")
    secret = os.environ.get(room["token"], "")
    if not 1 <= len(secret) <= 8192 or any(not 33 <= ord(char) <= 126 for char in secret):
        raise ValueError("Configura o token Matrix indicado para esta sala.")
    return room, secret


def fingerprint(room, secret):
    return hashlib.sha256(json.dumps([room["server"], room["room"], secret]).encode()).hexdigest()


def matrix_json(room, secret, route, *, data=None, params=None):
    endpoint = f"{room['server']}/_matrix/client/v3/rooms/{quote(room['room'], safe='')}/{route}"
    if params:
        endpoint += "?" + urlencode(params)
    headers = {"Accept": "application/json", "Authorization": "Bearer " + secret}
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    if payload is not None:
        headers["Content-Type"] = "application/json"
    try:
        request = Request(endpoint, data=payload, method="PUT" if payload is not None else "GET", headers=headers)
        with build_opener(NoRedirect()).open(request, timeout=8) as response:
            body = response.read(500_001)
        if len(body) > 500_000:
            raise ServiceError("A resposta do Matrix excedeu o limite de leitura.")
        decoded = json.loads(body)
        if not isinstance(decoded, dict):
            raise ValueError
        return decoded
    except HTTPError as error:
        with error:
            try:
                detail = json.loads(error.read(4000))
                code = detail.get("errcode") if isinstance(detail, dict) else None
            except (OSError, ValueError):
                code = None
            raise MatrixHTTP(error.code, code) from error
    except (URLError, OSError, ValueError) as error:
        raise ServiceError("Não consegui obter uma resposta válida do Matrix.") from error


def verify_unencrypted(room, secret):
    try:
        matrix_json(room, secret, "state/m.room.encryption/")
    except MatrixHTTP as error:
        if error.status == 404 and error.code == "M_NOT_FOUND":
            return
        raise
    raise ValueError("Esta sala usa cifragem. O envio Matrix do JARVIS suporta salas sem cifragem.")


def matrix_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if LIST.fullmatch(command):
        entries = rooms(memory)
        return response("\n".join(f"{key} · {'leitura e envio' if entry['write'] else 'leitura'}"
                                  for key, entry in entries.items()) or "Este perfil não tem salas Matrix configuradas.")
    if match := OPEN.fullmatch(command):
        room, _ = require_room(memory, match[1])
        url = "https://matrix.to/#/" + quote(room["room"], safe="")
        opened = webbrowser.open(url)
        detail = "Pedi ao navegador para abrir a sala." if opened else "A ligação à sala está disponível abaixo."
        return {"reply": detail, "links": [{"label": room["label"], "url": url}],
                "transient": True, "provider": "Matrix"}
    if match := READ.fullmatch(command):
        return read_messages(memory, match[1], match[2])
    if match := PREPARE.fullmatch(command):
        return prepare(memory, match[1], match[2])
    if match := CONFIRM.fullmatch(command):
        return confirm(memory, int(match[1]), match[2].casefold())
    if match := CANCEL.fullmatch(command):
        row = memory.execute(
            "UPDATE matrix_outbox SET state='cancelada', message='' WHERE id=? AND state='a rever' RETURNING id",
            (int(match[1]),),
        )
        return response("Confirmação Matrix cancelada." if row else "A mensagem não está a aguardar confirmação.")
    if match := STATUS.fullmatch(command):
        row, _, _ = authorized_row(memory, int(match[1]))
        return submission_result(row)
    return None


def read_messages(memory, label, query):
    room, secret = require_room(memory, label)
    result = matrix_json(room, secret, "messages", params={"dir": "b", "limit": 30})
    events = result.get("chunk")
    if not isinstance(events, list):
        raise ServiceError("O Matrix não devolveu uma lista de mensagens válida.")
    lines = [f"Mensagens recentes · {room['label']}"]
    query = query.strip().casefold() if query else ""
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "m.room.message":
            continue
        content = event.get("content")
        body = content.get("body") if isinstance(content, dict) else None
        if not isinstance(body, str) or query not in body.casefold():
            continue
        if content.get("msgtype") not in ("m.text", "m.notice", "m.emote"):
            continue
        author = event.get("sender")
        event_id = event.get("event_id")
        sent = event.get("origin_server_ts")
        when = datetime.fromtimestamp(sent / 1000, tz=timezone.utc).strftime("%d/%m %H:%M UTC") if type(sent) is int and 0 <= sent <= 32_503_680_000_000 else "sem data"
        lines.extend([f"{when} · {author} · {event_id}", " ".join(body.split())[:400]])
        if len(lines) >= 21:
            break
    if len(lines) == 1:
        lines.append("Sem correspondências de texto nas mensagens recentes acessíveis.")
    return response("\n".join(lines))


def prepare(memory, label, body):
    room, secret = require_room(memory, label, writing=True)
    if not body.strip():
        raise ValueError("Escreve o corpo da mensagem.")
    verify_unencrypted(room, secret)
    token = uuid4().hex
    row = memory.execute(
        "INSERT INTO matrix_outbox (room, fingerprint, transaction_id, message) VALUES (?, ?, ?, ?) RETURNING id",
        (room["label"], fingerprint(room, secret), token, body.strip()),
    )[0]
    identifier = row["id"]
    return response(
        f"Revisão Matrix {identifier} · sala {room['label']} · {room['server']}\n\n{body.strip()}\n\n"
        f"Para enviar, pede «Confirma a mensagem Matrix {identifier} com {token[:8]}».\n"
        f"Para recusar, pede «Cancela a mensagem Matrix {identifier}»."
    )


def authorized_row(memory, identifier):
    attempts = memory.execute("SELECT * FROM matrix_outbox WHERE id=?", (identifier,))
    if not attempts:
        raise ValueError("Não encontrei essa mensagem Matrix no perfil atual.")
    row = attempts[0]
    room, secret = require_room(memory, row["room"], writing=True)
    if fingerprint(room, secret) != row["fingerprint"]:
        raise ValueError("A sala ou a credencial mudou desde a revisão.")
    return row, room, secret


def confirm(memory, identifier, code):
    row, room, secret = authorized_row(memory, identifier)
    if row["transaction_id"][:8] != code:
        raise ValueError("O código de confirmação não corresponde à revisão.")
    if row["state"] == "enviada":
        return submission_result(row)
    if row["state"] not in ("a rever", "por confirmar"):
        raise ValueError("Esta mensagem já não pode ser confirmada.")
    verify_unencrypted(room, secret)
    claimed = memory.execute(
        """UPDATE matrix_outbox SET state='por confirmar' WHERE id=? AND state IN ('a rever','por confirmar')
           RETURNING transaction_id""", (identifier,),
    )
    if not claimed:
        current, _, _ = authorized_row(memory, identifier)
        return submission_result(current)
    try:
        result = matrix_json(room, secret, "send/m.room.message/" + quote(row["transaction_id"], safe=""),
                             data={"msgtype": "m.text", "body": row["message"]})
        registered = result.get("event_id")
        if not isinstance(registered, str) or not registered.startswith("$"):
            raise ServiceError("O Matrix respondeu sem indicar a referência do evento.")
        memory.execute("UPDATE matrix_outbox SET state='enviada', event_id=? WHERE id=?",
                       (registered[:500], identifier))
    except ServiceError:
        # The same transaction is reused even when the first answer could not be trusted.
        pass
    return submission_result(authorized_row(memory, identifier)[0])


def response(reply):
    return {"reply": reply, "transient": True, "provider": "Matrix"}


def submission_result(row):
    reply = f"Mensagem Matrix {row['id']} · {row['state']}"
    if row["event_id"]:
        reply += f"\nReferência — {row['event_id']}"
    if row["state"] == "por confirmar":
        reply += "\nA referência ainda está por confirmar. Podes repetir a mesma confirmação para consultar a mesma transação."
    return response(reply)
