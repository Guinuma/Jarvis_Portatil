"""Envio de versões revistas, com registo persistente de cada tentativa."""
import contextlib
import imaplib
import json
import re
import smtplib
import ssl
from datetime import datetime, timezone
from email.utils import format_datetime, make_msgid

from jarvis.messaging.imap import account_draft_allowed, authenticate, configured_accounts, imap_string, require_account, secret_for
from jarvis.integrations.mail_draft import address_list, build_draft

QUERY = re.compile(
    r'(?:jarvis,\s*)?(?:já enviaste o email(?: da tarefa (\d{1,18}))?|verifica o envio da tarefa (\d{1,18}))[.!?]?',
    re.I,
)


def sending_account(memory, identifier):
    if not isinstance(identifier, str):
        raise ValueError("Escolhe uma conta de envio autorizada.")
    account = require_account(memory, identifier)
    if not account["smtp"]:
        raise ValueError("Essa conta ainda não tem envio SMTP configurado.")
    return account


def available_senders(memory):
    try:
        accounts = configured_accounts(memory.path.stem)
    except ValueError:
        return []
    return [{"id": entry["id"], "sender": entry["smtp"]["sender"]}
            for entry in accounts.values() if entry["smtp"]]


def approval_for(memory, draft, identifier):
    account = sending_account(memory, identifier)
    addresses = address_list(draft["recipient"])
    if not addresses:
        raise ValueError("Guarda pelo menos um destinatário antes de preparar o envio.")
    return {"account": account["id"], "sender": account["smtp"]["sender"],
            "account_identity": account["identity"], "smtp_identity": account["smtp"]["identity"]}


def last_send(memory, identifier):
    rows = memory.execute(
        """SELECT revision, account_id, identity, smtp_identity, message_id, status, detail, sent_at
           FROM mail_sends WHERE workflow_id=?""", (identifier,),
    )
    return rows[0] if rows else None


def authorize_approval(memory, approval):
    account = sending_account(memory, approval["account"])
    if (account["identity"] != approval["account_identity"]
            or account["smtp"]["identity"] != approval["smtp_identity"]):
        raise ValueError("A configuração da conta mudou. Prepara e revê o envio novamente.")
    return account


def public_send(memory, identifier):
    attempt = last_send(memory, identifier)
    if not attempt:
        return None
    try:
        account = sending_account(memory, attempt["account_id"])
    except ValueError:
        return {"status": "conta indisponível", "revision": attempt["revision"]}
    if account["identity"] != attempt["identity"] or account["smtp"]["identity"] != attempt["smtp_identity"]:
        return {"status": "conta indisponível", "revision": attempt["revision"]}
    return {name: attempt[name] for name in ("revision", "account_id", "message_id", "status", "detail", "sent_at")}


def connect_smtp(settings):
    context = ssl.create_default_context()
    if settings["mode"] == "ssl":
        return smtplib.SMTP_SSL(settings["host"], settings["port"], context=context, timeout=12)
    client = smtplib.SMTP(settings["host"], settings["port"], timeout=12)
    try:
        client.starttls(context=context)
    except Exception:
        client.close()
        raise
    return client


def smtp_auth(client, settings, secret):
    if settings["auth"] == "xoauth2":
        initial = f"user={settings['username']}\x01auth=Bearer {secret}\x01\x01"
        client.ehlo_or_helo_if_needed()
        client.auth("XOAUTH2", lambda challenge=None: "" if challenge else initial)
    else:
        client.login(settings["username"], secret)


def finish_send(memory, identifier, message_id, status, detail):
    moment = datetime.now(timezone.utc).isoformat(timespec="seconds")
    memory.execute(
        """UPDATE mail_sends SET status=?, detail=?, sent_at=?
           WHERE workflow_id=? AND message_id=?""",
        (status, detail, moment, identifier, message_id),
    )


def claim_send(memory, row, approval, message_id):
    result = memory.execute(
        """INSERT INTO mail_sends
           (workflow_id, revision, account_id, identity, smtp_identity, message_id, status, detail)
           SELECT id, revision, ?, ?, ?, ?, 'por confirmar', ? FROM workflows
           WHERE id=? AND revision=? AND status='concluída'
           ON CONFLICT(workflow_id) DO UPDATE SET
               revision=excluded.revision, account_id=excluded.account_id, identity=excluded.identity,
               smtp_identity=excluded.smtp_identity, message_id=excluded.message_id, status=excluded.status,
               detail=excluded.detail, sent_at=NULL
           WHERE mail_sends.status='recusado' AND mail_sends.revision<>excluded.revision
           RETURNING workflow_id""",
        (approval["account"], approval["account_identity"], approval["smtp_identity"], message_id,
         "A tentativa está em curso ou ficou por confirmar.", row["id"], row["revision"]),
    )
    if not result:
        raise ValueError("A revisão mudou ou já existe uma tentativa para esta versão. Consulta o estado do envio.")


def send_reviewed(memory, root, row, confirm):
    if confirm is not True:
        raise ValueError("Confirma o envio da versão revista.")
    data = json.loads(row["data"])
    approval = data.get("send_approval")
    if not approval or row["status"] != "concluída":
        raise ValueError("Prepara e revê o envio antes de confirmar.")
    account = authorize_approval(memory, approval)
    settings = account["smtp"]
    secret = secret_for(settings)
    message = build_draft(root, data["draft"], data.get("attachments", []), data.get("thread"))
    if not message.get("To"):
        raise ValueError("Coloca pelo menos um destinatário no rascunho.")
    addresses = tuple(dict.fromkeys(value.addr_spec for value in message["To"].addresses))
    sender = address_list(settings["sender"])[0]
    message_id = make_msgid(domain=sender.domain.encode("idna").decode("ascii"))
    message["From"] = sender
    message["Date"] = format_datetime(datetime.now(timezone.utc))
    message["Message-ID"] = message_id
    claim_send(memory, row, approval, message_id)
    try:
        client = connect_smtp(settings)
    except OSError:
        finish_send(memory, row["id"], message_id, "recusado", "Falhou a ligação SMTP segura antes de enviar.")
        return
    with contextlib.closing(client):
        try:
            smtp_auth(client, settings, secret)
        except OSError:
            finish_send(memory, row["id"], message_id, "recusado", "A autenticação SMTP falhou antes de enviar.")
            return
        try:
            rejected = client.send_message(message, from_addr=sender.addr_spec, to_addrs=addresses)
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError,
                smtplib.SMTPNotSupportedError, smtplib.SMTPHeloError):
            finish_send(memory, row["id"], message_id, "recusado", "O servidor SMTP recusou a mensagem.")
        except OSError:
            finish_send(memory, row["id"], message_id, "por confirmar",
                        "A ligação terminou sem confirmação. Verifica Enviados antes de tomar outra ação.")
        else:
            state = "parcial" if rejected else "enviado"
            info = ("Aceite em parte. Destinatários recusados: " + ", ".join(addr for addr in addresses if addr in rejected)
                    if rejected else "O servidor SMTP aceitou a mensagem para os destinatários revistos.")
            finish_send(memory, row["id"], message_id, state, info)


def found_in_sent(account, message_id):
    folder = account["sent"]
    if not folder:
        raise ValueError("Configura uma pasta Enviados autorizada para verificar esta tentativa.")
    return found_in_folder(account, folder, message_id)


def found_in_folder(account, folder, message_id):
    if folder not in account["folders"]:
        raise ValueError("Essa pasta não está autorizada para verificar a tentativa.")
    secret = secret_for(account)
    try:
        with imaplib.IMAP4_SSL(account["host"], account["port"], ssl_context=ssl.create_default_context(),
                              timeout=8) as client:
            authenticate(client, account, secret)
            status, _ = client.select(imap_string(folder), readonly=True)
            if status != "OK":
                raise ValueError("A pasta de email recusou a consulta.")
            status, rows = client.uid("SEARCH", None, "HEADER", "Message-ID", imap_string(message_id))
            if status != "OK":
                raise ValueError("A pesquisa do Message-ID na pasta indicada falhou.")
            for uid in (rows[0] or b"").split()[-10:]:
                if not uid.isdigit():
                    continue
                status, headers = client.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
                if status == "OK" and any(isinstance(item, tuple) and len(item) == 2
                                           and exact_id(item[1], message_id) for item in headers):
                    return True
            return False
    except (imaplib.IMAP4.error, OSError) as error:
        raise ValueError("Não consegui verificar o Message-ID no serviço de email.") from error


def exact_id(content, message_id):
    if not isinstance(content, bytes):
        return False
    for line in content.splitlines():
        key, _, value = line.partition(b":")
        if key.lower() == b"message-id" and value.strip() == message_id.encode("ascii"):
            return True
    return False


def send_status_command(text, memory):
    match = QUERY.fullmatch(text)
    if not match:
        return None
    number = match[1] or match[2]
    if not number:
        rows = memory.execute("SELECT workflow_id FROM mail_sends ORDER BY workflow_id DESC LIMIT 2")
        if not rows:
            return "Ainda não há envios registados neste perfil."
        if len(rows) > 1:
            return "Qual email? Indica o número da tarefa ou consulta o estado no painel."
        number = rows[0]["workflow_id"]
    return verify_send_status(memory, int(number))


def verify_send_status(memory, identifier):
    workflows = memory.execute("SELECT data FROM workflows WHERE id=?", (identifier,))
    if workflows and not account_draft_allowed(memory, json.loads(workflows[0]["data"])):
        raise ValueError("O estado deste rascunho não está disponível neste perfil.")
    attempt = last_send(memory, identifier)
    if not attempt:
        return "Essa tarefa ainda não tem uma tentativa de envio registada."
    account = sending_account(memory, attempt["account_id"])
    if attempt["identity"] != account["identity"] or attempt["smtp_identity"] != account["smtp"]["identity"]:
        raise ValueError("O envio pertence a uma configuração de conta diferente.")
    detail, state = attempt["detail"], attempt["status"]
    if state == "por confirmar":
        if found_in_sent(account, attempt["message_id"]):
            state = "encontrado em enviados"
            detail = "O Message-ID foi confirmado na pasta Enviados."
            memory.execute(
                """UPDATE mail_sends SET status=?, detail=?, sent_at=?
                   WHERE workflow_id=? AND message_id=? AND status='por confirmar'""",
                (state, detail, datetime.now(timezone.utc).isoformat(timespec="seconds"), identifier, attempt["message_id"]),
            )
        else:
            detail = "Ainda não encontrei o Message-ID em Enviados. O estado continua por confirmar."
            memory.execute(
                """UPDATE mail_sends SET detail=?
                   WHERE workflow_id=? AND message_id=? AND status='por confirmar'""",
                (detail, identifier, attempt["message_id"]),
            )
        if current := last_send(memory, identifier):
            state, detail = current["status"], current["detail"]
    return f"Tarefa {identifier} · {state}\n{detail}\nReferência — {attempt['message_id']}"
