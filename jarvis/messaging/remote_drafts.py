"""Criar uma cópia de um rascunho revisto numa pasta IMAP autorizada."""
import imaplib
import json
import ssl
from datetime import datetime, timezone
from email.utils import format_datetime, make_msgid

from jarvis.messaging.imap import authenticate, configured_accounts, imap_string, require_account, secret_for
from jarvis.integrations.mail_draft import address_list, build_draft
from jarvis.messaging.smtp import found_in_folder


def draft_destinations(memory):
    try:
        accounts = configured_accounts(memory.path.stem)
    except ValueError:
        return []
    return [{"id": account["id"], "folder": account["drafts"]}
            for account in accounts.values() if account["drafts"]]


def remote_drafts(memory, workflow_id, revision):
    rows = memory.execute(
        """SELECT account_id, identity, folder, message_id, state FROM remote_drafts
           WHERE workflow_id=? AND revision=? ORDER BY account_id""", (workflow_id, revision),
    )
    try:
        accounts = configured_accounts(memory.path.stem)
    except ValueError:
        return []
    visible = []
    for row in rows:
        account = accounts.get(row["account_id"])
        if account and account["identity"] == row["identity"] and account["drafts"] == row["folder"]:
            visible.append({key: row[key] for key in ("account_id", "folder", "message_id", "state")})
    return visible


def store_remote_draft(memory, root, row, identifier):
    if not isinstance(identifier, str):
        raise ValueError("Escolhe uma conta de destino para o rascunho.")
    account = require_account(memory, identifier)
    folder = account["drafts"]
    data = json.loads(row["data"])
    if not folder or "draft" not in data or row["status"] != "concluída":
        raise ValueError("A conta precisa de uma pasta de rascunhos autorizada e uma revisão guardada.")
    keys = (row["id"], row["revision"], account["id"])
    attempts = memory.execute(
        "SELECT * FROM remote_drafts WHERE workflow_id=? AND revision=? AND account_id=?", keys,
    )
    if attempts:
        attempt = attempts[0]
        if attempt["identity"] != account["identity"] or attempt["folder"] != folder:
            raise ValueError("A conta ou pasta de destino mudou. Guarda e revê o rascunho novamente.")
        if attempt["state"] == "por confirmar" and found_in_folder(account, folder, attempt["message_id"]):
            set_state(memory, keys, "guardado")
        return
    secret = secret_for(account)
    message = build_draft(root, data["draft"], data.get("attachments", []), data.get("thread"))
    if account["smtp"]:
        message["From"] = address_list(account["smtp"]["sender"])[0]
    message["Date"] = format_datetime(datetime.now(timezone.utc))
    message_id = make_msgid(domain="jarvis.local")
    message["Message-ID"] = message_id
    content = message.as_bytes()
    claimed = memory.execute(
        """INSERT INTO remote_drafts (workflow_id, revision, account_id, identity, folder, message_id, state)
           SELECT id, revision, ?, ?, ?, ?, 'por confirmar' FROM workflows
           WHERE id=? AND revision=? AND status='concluída'
           ON CONFLICT(workflow_id, revision, account_id) DO NOTHING RETURNING workflow_id""",
        (account["id"], account["identity"], folder, message_id, row["id"], row["revision"]),
    )
    if not claimed:
        raise ValueError("A revisão mudou ou já existe uma tentativa para esta cópia.")
    writing = False
    try:
        with imaplib.IMAP4_SSL(account["host"], account["port"], ssl_context=ssl.create_default_context(),
                              timeout=10) as client:
            authenticate(client, account, secret)
            writing = True
            outcome, _ = client.append(imap_string(folder), "\\Draft", None, content)
            set_state(memory, keys, "guardado" if outcome == "OK" else "recusado")
    except (OSError, imaplib.IMAP4.error):
        if not writing:
            set_state(memory, keys, "recusado")


def set_state(memory, keys, state):
    memory.execute(
        """UPDATE remote_drafts SET state=? WHERE workflow_id=? AND revision=? AND account_id=? AND state='por confirmar'""",
        (state, *keys),
    )
