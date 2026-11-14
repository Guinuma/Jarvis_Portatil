"""Agendamento local do modo programação."""
import json
import re
from datetime import datetime, timedelta

from .agenda import agenda_command
from .integrations.editor import open_project, resolve_project
from .integrations.project_files import file_command, safe_path
from .integrations.notes import latest_notes


def schedule_programming(memory, when):
    memory.execute("INSERT INTO routines (due, status) VALUES (?, 'pendente')", (when.timestamp(),))
    return f"Modo programação agendado para {when:%d/%m/%Y às %H:%M}."


def run_programming(root):
    open_project(root)
    session, paths = latest_notes(root)
    for path in paths:
        open_project(root, target=root / path)
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


def daily_routine(command, memory, root):
    if command == "modo estudo":
        records = memory.execute("SELECT value FROM memories WHERE name = 'projeto de estudo' AND kind = 'projeto'")
        if not records:
            return "Define uma memória do tipo projeto com o nome «projeto de estudo» e o nome de um projeto autorizado."
        matches = resolve_project(records[0]["value"], root)
        if len(matches) != 1:
            return "O projeto de estudo tem de identificar uma única pasta autorizada."
        name, folder = matches[0]
        open_project(folder)
        return f"Modo estudo: pedi ao VS Code para abrir {name}."
    if command == "bom dia":
        return agenda_command("Mostra a agenda", memory) + "\n\n" + agenda_command("Mostra as tarefas", memory)
    if command == "fecha o dia":
        pending = agenda_command("Mostra as tarefas", memory)
        saved = file_command("Guarda uma nota Fecho do dia · " + pending.replace("\n", " · "), root)
        return pending + "\n\n" + saved
    if command == "faz como da ultima vez":
        completed = memory.execute(
            "SELECT id FROM routines WHERE status = 'concluída' ORDER BY finished DESC LIMIT 1"
        )
        if not completed:
            return "Ainda não há uma execução do modo programação para repetir."
        return "A última rotina registada foi o modo programação. Diz «ativa o modo programação» para repetir."
    return None

FILE_RULE = re.compile(
    r'quando aparecer "([^"]+)"(?: e existir "([^"]+)")?, ativa o modo programação[.!]?',
    re.I,
)


def file_rule_command(command, memory, root):
    match = FILE_RULE.fullmatch(command)
    if not match:
        return None
    event, condition = match.groups()
    event = safe_path(root, event).relative_to(root).as_posix()
    condition = safe_path(root, condition).relative_to(root).as_posix() if condition else None
    if (root / event).exists():
        raise ValueError("O ficheiro do evento já existe. Indica um ficheiro que ainda não esteja presente.")
    memory.execute("INSERT INTO file_rules (event_path, condition_path) VALUES (?, ?)", (event, condition))
    requirement = f" e existir {condition}" if condition else ""
    return f"Regra guardada: quando aparecer {event}{requirement}, vou ativar o modo programação."


def check_file_rules(memory, root):
    rules = memory.execute("SELECT * FROM file_rules WHERE status = 'pendente'")
    for rule in rules:
        try:
            appeared = safe_path(root, rule["event_path"]).is_file()
            condition = rule["condition_path"]
            allowed = not condition or safe_path(root, condition).is_file()
        except (OSError, ValueError, RuntimeError):
            continue
        if not appeared or not allowed:
            continue
        claimed = memory.execute(
            """UPDATE file_rules SET status = 'em execução' WHERE id = ? AND status = 'pendente' RETURNING id""",
            (rule["id"],),
        )
        if claimed:
            result = run_now(memory, root)
            memory.execute("UPDATE file_rules SET status=?, result=? WHERE id=?", (
                "falhou" if "erro" in result else "concluída", json.dumps(result, ensure_ascii=False), rule["id"],
            ))