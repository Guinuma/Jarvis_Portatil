"""Fluxo persistente de comparação de PDFs e preparação de rascunhos locais."""
import json
import logging
import re
from pathlib import Path
import time
from uuid import uuid4

from jarvis.messaging.imap import account_draft_allowed, account_reply_input
from .integrations.compare import compare_documents, comparison_sources, comparison_text
from jarvis.messaging.local_mail import reply_input
from jarvis.messaging.remote_drafts import draft_destinations, remote_drafts, store_remote_draft
from .integrations.mail_draft import export_draft, review_attachments
from jarvis.messaging.smtp import approval_for, available_senders, public_send, send_reviewed, verify_send_status
from .integrations.project_files import safe_path, search

REQUEST = re.compile(
    r'(?:jarvis,\s*)?(?:compara versões do pdf "([^"]+)" e prepara um email'
    r'|encontra o pdf d[oea] (.+?),?\s+compara-o com a versão anterior e prepara um email(?: com as alterações)?)[.!]?',
    re.I,
)
STEPS = ["Selecionar as versões", "Comparar os PDFs", "Preparar o rascunho"]
ACTIVE = {"na fila", "em execução"}
REPLY_STEPS = ["Preparar a resposta"]


def workflow_command(text, memory, root):
    if draft := (account_reply_input(text, memory) or reply_input(text, root)):
        row = memory.execute(
            "INSERT INTO workflows (step, status, data) VALUES (1, 'concluída', ?) RETURNING id",
            (serialize(draft),),
        )[0]
        return {"reply": "Rascunho de resposta preparado. Revê-o no painel de tarefas.",
                "workflow": row["id"]}
    match = REQUEST.fullmatch(text.strip())
    if not match:
        return None
    query = (match[1] or match[2]).strip()
    if not query:
        raise ValueError("Indica parte do nome dos PDFs a procurar.")
    candidates = search(root, query, content=False, suffix=".pdf")
    payload = {"candidates": candidates}
    row = memory.execute(
        "INSERT INTO workflows (step, status, data) VALUES (0, 'a rever', ?) RETURNING id",
        (serialize(payload),),
    )[0]
    return {"reply": f"Tarefa {row['id']} criada. Escolhe as duas versões no painel de tarefas.",
            "workflow": row["id"]}


def serialize(data):
    return json.dumps(data, ensure_ascii=False)


def list_workflows(memory):
    tasks = memory.execute("SELECT id, step, status, revision, data FROM workflows ORDER BY id DESC LIMIT 30")
    visible = []
    senders = available_senders(memory)
    destinations = draft_destinations(memory)
    for task in tasks:
        data = json.loads(task["data"])
        if not account_draft_allowed(memory, data):
            continue
        if "draft" in data:
            task["senders"] = senders
            task["draft_destinations"] = destinations
            task["remote_drafts"] = remote_drafts(memory, task["id"], task["revision"])
            task["submission"] = public_send(memory, task["id"])
            if preparation := data.get("send_approval"):
                task["approval"] = {key: preparation[key] for key in ("account", "sender")}
            data.pop("send_approval", None)
        task["data"] = data
        task["steps"] = REPLY_STEPS if data.get("kind") == "mail_reply" else STEPS
        visible.append(task)
    return visible


def current_workflow(memory, request):
    identifier, revision = request["id"], request["revision"]
    if type(identifier) is not int or type(revision) is not int or not 0 < identifier < 2**63 or not 0 <= revision < 2**63:
        raise ValueError("Identificador de tarefa inválido.")
    rows = memory.execute("SELECT * FROM workflows WHERE id = ? AND revision = ?", (identifier, revision))
    if not rows:
        raise ValueError("A tarefa mudou. Atualiza o painel.")
    row = rows[0]
    if not account_draft_allowed(memory, json.loads(row["data"])):
        raise ValueError("O rascunho não está disponível para as contas autorizadas neste perfil.")
    return row


def export_workflow_draft(memory, root, request):
    row = current_workflow(memory, request)
    if row["status"] != "concluída":
        raise ValueError("Conclui a preparação do rascunho antes de o descarregar.")
    data = json.loads(row["data"])
    return export_draft(root, data["draft"], data.get("attachments", []), data.get("thread"))


def change_workflow(memory, root, request):
    action = request["action"]
    if action == "list":
        return list_workflows(memory)
    row = current_workflow(memory, request)
    identifier, revision = row["id"], row["revision"]
    step, status, data = row["step"], row["status"], json.loads(row["data"])
    if action == "send":
        send_reviewed(memory, root, row, request.get("confirm"))
        return list_workflows(memory)
    if action == "store_remote_draft":
        store_remote_draft(memory, root, row, request.get("account"))
        return list_workflows(memory)
    if action == "check_send":
        verify_send_status(memory, identifier)
        return list_workflows(memory)
    if action == "prepare_send" and status == "concluída" and "draft" in data:
        data["send_approval"] = approval_for(memory, data["draft"], request["account"])
    elif action == "cancel_send" and data.get("send_approval"):
        data.pop("send_approval")
    elif action == "select" and step == 0 and status == "a rever":
        if not all(isinstance(request[key], str) and request[key].strip() for key in ("old", "new")):
            raise ValueError("Indica as duas versões do PDF.")
        before, after = [safe_path(root, request[key]) for key in ("old", "new")]
        if before == after or any(p.suffix.lower() != ".pdf" or not p.is_file() for p in (before, after)):
            raise ValueError("Escolhe dois PDFs diferentes no projeto.")
        data.update(old=before.relative_to(root).as_posix(), new=after.relative_to(root).as_posix())
        step, status = 1, "na fila"
    elif action == "retry" and status == "falhou":
        data.pop("error", None)
        status = "na fila"
    elif action == "files" and step == 1 and status in {"falhou", "na fila"}:
        data.pop("error", None)
        step, status = 0, "a rever"
    elif action == "draft" and status == "concluída" and "draft" in data:
        limits = {"recipient": 320, "subject": 300, "body": 30_000}
        draft = {key: request[key] for key in limits}
        if (any(not isinstance(value, str) or len(value) > limits[key] for key, value in draft.items())
                or not draft["subject"].strip() or not draft["body"].strip()
                or any("\n" in draft[key] or "\r" in draft[key] for key in ("recipient", "subject"))):
            raise ValueError("Revê o destinatário, o assunto e o texto do rascunho.")
        if "attachments" in request:
            data["attachments"] = review_attachments(root, request["attachments"])
        data["draft"] = draft
        data.pop("send_approval", None)
    elif action == "cancel" and (status in ACTIVE or status in {"a rever", "falhou"}):
        status = "cancelada"
    else:
        raise ValueError("Esta ação já não está disponível para a tarefa.")
    updated = memory.execute(
        """UPDATE workflows SET step=?, status=?, data=?, revision=revision+1, claim=NULL, lease=NULL
           WHERE id=? AND revision=? AND NOT EXISTS (
               SELECT 1 FROM mail_sends WHERE workflow_id=workflows.id AND status<>'recusado'
           ) RETURNING id""",
        (step, status, serialize(data), identifier, revision),
    )
    if not updated:
        raise ValueError("A tarefa mudou. Atualiza o painel.")
    return list_workflows(memory)


def process_workflow(memory, root):
    now = time.time()
    token = uuid4().hex
    rows = memory.execute(
        """UPDATE workflows SET status='em execução', claim=?, lease=?, revision=revision+1
           WHERE id=(SELECT id FROM workflows
                     WHERE status='na fila' OR (status='em execução' AND lease < ?)
                     ORDER BY id LIMIT 1) RETURNING id, step, data""",
        (token, now + 120, now),
    )
    if not rows:
        return
    row = rows[0]
    step, data = row["step"], json.loads(row["data"])
    try:
        if step == 1:
            result = compare_documents(root, data["old"], data["new"])
            data["comparison"] = comparison_text(result)
            data["sources"] = comparison_sources(result)
        else:
            data["draft"] = {
                "recipient": "",
                "subject": "Alterações ao documento " + Path(data["new"]).name,
                "body": f"Olá,\n\nSegue a comparação entre as duas versões do documento.\n\n"
                        f"{data['comparison']}\n\nCumprimentos",
            }
        step += 1
        status = "concluída" if step == len(STEPS) else "na fila"
    except (OSError, ValueError, RuntimeError) as error:
        status = "falhou"
        data["error"] = str(error)
    except Exception:
        logging.exception("Falha ao executar o passo %s da tarefa %s", step, row["id"])
        status = "falhou"
        data["error"] = "Não consegui concluir este passo. Revê os ficheiros e tenta novamente."
    memory.execute(
        """UPDATE workflows SET step=?, status=?, data=?, revision=revision+1, claim=NULL, lease=NULL
           WHERE id=? AND claim=?""",
        (step, status, serialize(data), row["id"], token),
    )
