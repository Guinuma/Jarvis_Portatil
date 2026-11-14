"""Agendamento local do modo programação."""
import json
from datetime import datetime, timedelta

from .integrations.editor import open_project
from .integrations.notes import latest_notes


def schedule_programming(memory, when):
    memory.execute("INSERT INTO routines (due, status) VALUES (?, 'pendente')", (when.timestamp(),))
    return f"Modo programação agendado para {when:%d/%m/%Y às %H:%M}."


def run_programming(root):
    open_project(root)
    session, paths = latest_notes(root)
    return {"projeto": str(root), "sessão": session.isoformat() if session else None, "notas": paths}


def run_now(memory, root):
    row = memory.execute(
        "INSERT INTO routines (due, status) VALUES (?, 'em execução') RETURNING id",
        (datetime.now().timestamp(),),
    )[0]
    return finish_run(memory, root, row["id"])


def finish_run(memory, root, task_id):
    try:
        result = run_programming(root)
        status = "concluída"
    except (OSError, ValueError, RuntimeError) as error:
        result = {"erro": str(error)}
        status = "falhou"
    memory.execute(
        "UPDATE routines SET status = ?, result = ?, finished = ? WHERE id = ?",
        (status, json.dumps(result, ensure_ascii=False), datetime.now().timestamp(), task_id),
    )
    return result


def run_due(memory, root, now=None):
    now = datetime.now().timestamp() if now is None else now
    tasks = memory.execute(
        """UPDATE routines SET status = 'em execução'
        WHERE status = 'pendente' AND due <= ? RETURNING id""", (now,),
    )
    for task in tasks:
        finish_run(memory, root, task["id"])


def tomorrow_at_nine(now=None):
    return ((now or datetime.now()) + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
