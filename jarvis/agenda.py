"""Agenda local do perfil JARVIS."""
import re
from datetime import date, datetime, timedelta

CREATE = re.compile(r'(cria um evento|reserva um bloco de foco) "([^"]+)" em (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) por (\d+) minutos[.!]?', re.I)
MOVE = re.compile(r'reagenda o evento (\d+) para (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})[.!]?', re.I)
DAY = re.compile(r'(?:mostra|consulta) (?:a )?agenda(?: (?:de )?(hoje|amanhã|\d{4}-\d{2}-\d{2}))?[.!]?', re.I)


def agenda_command(text, memory):
    alert = re.fullmatch(r"avisa-me (\d+) minutos antes do evento (\d+)[.!]?", text, re.I)
    if alert:
        lead, event_id = map(int, alert.groups())
        if not 0 <= lead <= 10080:
            raise ValueError("Escolhe uma antecedência entre 0 e 10080 minutos.")
        rows = memory.execute(
            """INSERT INTO event_alerts (event_id, lead, sent)
            SELECT id, ?, 0 FROM agenda WHERE id = ?
            ON CONFLICT(event_id) DO UPDATE SET lead=excluded.lead, sent=0 RETURNING event_id""",
            (lead, event_id),
        )
        return "Aviso associado ao evento." if rows else "Não encontrei esse evento."
    task = re.fullmatch(r'cria a tarefa recorrente "([^"]+)" a cada (\d+) dias desde (\d{4}-\d{2}-\d{2})', text, re.I)
    if task:
        days = int(task[2])
        if not 1 <= days <= 365:
            raise ValueError("Escolhe uma frequência entre 1 e 365 dias.")
        due = date.fromisoformat(task[3]).isoformat()
        row = memory.execute(
            "INSERT INTO tasks (title, due, days) VALUES (?, ?, ?) RETURNING id", (task[1], due, days)
        )[0]
        return f"Tarefa {row['id']} criada. Próxima ocorrência em {due}."
    done = re.fullmatch(r"conclui a tarefa (\d+)[.!]?", text, re.I)
    if done:
        rows = memory.execute(
            """UPDATE tasks SET due = date(due, '+' || days || ' days')
               WHERE id = ? RETURNING due""", (int(done[1]),)
        )
        return f"Próxima ocorrência em {rows[0]['due']}." if rows else "Não encontrei essa tarefa."
    if text.casefold().rstrip(".!?") == "mostra as tarefas":
        rows = memory.execute("SELECT * FROM tasks ORDER BY due, id")
        return "\n".join(f"{row['due']} · tarefa {row['id']} · {row['title']}" for row in rows) or "Sem tarefas recorrentes."
    if match := DAY.fullmatch(text):
        value = (match[1] or "hoje").casefold()
        day = date.today()
        if value == "amanhã":
            day += timedelta(days=1)
        elif value != "hoje":
            day = date.fromisoformat(value)
        start = datetime.combine(day, datetime.min.time()).timestamp()
        end = datetime.combine(day + timedelta(days=1), datetime.min.time()).timestamp()
        rows = memory.execute(
            "SELECT * FROM agenda WHERE starts < ? AND ends > ? ORDER BY starts, id", (end, start)
        )
        return "\n".join(
            f'{datetime.fromtimestamp(row["starts"]):%H:%M} · {row["title"]} · evento {row["id"]}'
            for row in rows
        ) or f"A agenda local está livre em {day:%d/%m/%Y}."

    create = CREATE.fullmatch(text)
    move = MOVE.fullmatch(text)
    if not create and not move:
        return None
    match = create or move
    when = datetime.fromisoformat(f"{match[3 if create else 2]}T{match[4 if create else 3]}")
    start = when.timestamp()
    if create:
        minutes = int(create[5])
        if not 1 <= minutes <= 1440:
            raise ValueError("Escolhe entre 1 e 1440 minutos.")
        end = start + minutes * 60
        rows = memory.execute(
            """INSERT INTO agenda(title, starts, ends)
               SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM agenda WHERE starts < ? AND ends > ?)
               RETURNING id""", (create[2], start, end, end, start),
        )
        title = create[2]
        old_id = 0
    else:
        old_id = int(move[1])
        events = memory.execute("SELECT * FROM agenda WHERE id = ?", (old_id,))
        if not events:
            return "Não encontrei esse evento na agenda local."
        event = events[0]
        end = start + event["ends"] - event["starts"]
        title = event["title"]
        rows = memory.execute(
            """UPDATE agenda SET starts = ?, ends = ? WHERE id = ?
               AND NOT EXISTS (SELECT 1 FROM agenda WHERE id != ? AND starts < ? AND ends > ?)
               RETURNING id""", (start, end, old_id, old_id, end, start),
        )
    if not rows:
        overlaps = memory.execute(
            "SELECT title FROM agenda WHERE id != ? AND starts < ? AND ends > ? ORDER BY starts",
            (old_id, end, start),
        )
        return "Conflito na agenda local: " + ", ".join(row["title"] for row in overlaps)
    return f'{title} · {when:%d/%m/%Y às %H:%M} · agenda local · evento {rows[0]["id"]}.'


def due_alerts(memory, now=None):
    now = datetime.now().timestamp() if now is None else now
    return memory.execute(
        """UPDATE event_alerts SET sent = 1 WHERE sent = 0 AND event_id IN (
            SELECT agenda.id FROM agenda JOIN event_alerts ON agenda.id = event_alerts.event_id
            WHERE agenda.starts - event_alerts.lead * 60 <= ? AND agenda.ends > ?
        ) RETURNING event_id, (SELECT title FROM agenda WHERE id = event_id) AS title""",
        (now, now),
    )