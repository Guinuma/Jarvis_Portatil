"""Preparar materiais e analisar transcrições locais de eventos da agenda."""
import json
import re
from collections import defaultdict
from datetime import datetime

from jarvis.integrations.project_files import SKIP, safe_path

EVENT_ID = r"(\d{1,18})"
NOTES = re.compile(rf"prepara notas para (?:o )?evento {EVENT_ID}(?: com (.+))?", re.I | re.S)
ANALYZE = re.compile(rf'analisa (?:a )?transcrição "([^"\r\n]{{1,500}})" do evento {EVENT_ID}[.!]?', re.I)
FOLLOWUP = re.compile(rf"prepara (?:o )?seguimento do evento {EVENT_ID}[.!]?", re.I)
MATERIALS = re.compile(rf"mostra (?:os )?materiais do evento {EVENT_ID}[.!]?", re.I)
SAVE_NOTES = re.compile(rf"guarda notas do evento {EVENT_ID} com (.+)", re.I | re.S)
TIMECODE = re.compile(r"^\s*((?:\d{2,}:)?\d{2}:\d{2}(?:[.,]\d{3})?)\s*-->")
MARKED_TIME = re.compile(r"^\[((?:\d{2,}:)?\d{2}:\d{2})]\s*")
MARKED_SECTION = re.compile(r"^(decis[aã]o|decidimos|ação|acção|tarefa|responsável|prazo)\s*[:–-]\s*", re.I)
TEXT_SOURCES = {".vtt", ".srt", ".md", ".txt"}
MAX_TEXT = 512_000


def meeting_command(text, memory, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := NOTES.fullmatch(command.rstrip(".!?")):
        number, payload = int(match[1]), match[2]
        event = event_row(memory, number)
        documents = review_documents(root, json.loads(payload) if payload else [])
        stamp = datetime.fromtimestamp(event["starts"]).strftime("%d/%m/%Y %H:%M")
        prepared = f"{event['title']} · {stamp}\n\nPontos a discutir\n\nDecisões\n\nTarefas e prazos"
        rows = memory.execute(
            """INSERT INTO meeting_materials (event_id, notes, documents) VALUES (?, ?, ?)
               ON CONFLICT(event_id) DO UPDATE SET
                   notes=CASE WHEN meeting_materials.notes='' THEN excluded.notes ELSE meeting_materials.notes END,
                   documents=CASE WHEN ? THEN excluded.documents ELSE meeting_materials.documents END
               RETURNING notes, documents""",
            (number, prepared, json.dumps(documents, ensure_ascii=False), payload is not None),
        )
        return result(rows[0]["notes"], json.loads(rows[0]["documents"]))
    if match := SAVE_NOTES.fullmatch(command):
        number, notes = int(match[1]), json.loads(match[2])
        event_row(memory, number)
        if not isinstance(notes, str) or not 1 <= len(notes.strip()) <= 6000:
            raise ValueError("Fornece as notas do evento numa frase ou texto JSON entre aspas.")
        memory.execute(
            """INSERT INTO meeting_materials (event_id, notes) VALUES (?, ?)
               ON CONFLICT(event_id) DO UPDATE SET notes=excluded.notes""", (number, notes.strip()),
        )
        return result(f"Notas guardadas no evento {number}.")
    if match := ANALYZE.fullmatch(command):
        number = int(match[2])
        event = event_row(memory, number)
        path = text_source(root, match[1])
        name = path.relative_to(root).as_posix()
        analysis = transcript_sections(read_source(root, name), path.suffix.lower())
        memory.execute(
            """INSERT INTO meeting_materials (event_id, transcript) VALUES (?, ?)
               ON CONFLICT(event_id) DO UPDATE SET transcript=excluded.transcript, followup=''""", (number, name),
        )
        return result(render_analysis(event["title"], analysis), [name])
    if match := FOLLOWUP.fullmatch(command):
        number = int(match[1])
        event = event_row(memory, number)
        record = materials_row(memory, number)
        transcript = record["transcript"]
        if not transcript:
            raise ValueError("Associa primeiro uma transcrição ao evento.")
        from jarvis.planning.meeting_analysis import inferred_followup

        source = read_source(root, transcript)
        analysis = transcript_sections(source, text_source(root, transcript).suffix.lower())
        marked = render_lists(analysis, ("Decisões", "Tarefas e prazos"))
        inferred = inferred_followup(memory, number, transcript, source)
        combined = "\n\n".join(filter(None, (marked, inferred)))
        if not combined:
            raise ValueError(f"Assinala decisões e tarefas na transcrição ou pede «Identifica decisões e tarefas do evento {number}».")
        followup = f"Assunto — Seguimento de {event['title']}\n\nOlá,\n\n{combined}\n\nCumprimentos"
        saved = memory.execute(
            "UPDATE meeting_materials SET followup=? WHERE event_id=? AND transcript=? RETURNING event_id",
            (followup, number, transcript),
        )
        if not saved:
            raise ValueError("A transcrição associada mudou. Prepara o seguimento novamente.")
        return result(followup, [transcript])
    if match := MATERIALS.fullmatch(command):
        number = int(match[1])
        event = event_row(memory, number)
        record = materials_row(memory, number)
        documents = json.loads(record["documents"])
        transcript = record["transcript"]
        sections = [f"Materiais do evento {number} · {event['title']}"]
        if record["notes"]:
            sections.append("Notas\n" + record["notes"])
        if transcript:
            sections.append(f"Transcrição — {transcript}")
        if record["followup"]:
            sections.append("Seguimento guardado\n" + record["followup"])
        return result("\n\n".join(sections), [*documents, *([transcript] if transcript else [])])
    return None


def result(text, paths=()):
    return {"reply": text, "documents": list(dict.fromkeys(paths))}


def event_row(memory, number):
    rows = memory.execute("SELECT title, starts FROM agenda WHERE id=?", (number,))
    if not rows:
        raise ValueError("Não encontrei esse evento na agenda local deste perfil.")
    return rows[0]


def materials_row(memory, number):
    rows = memory.execute("SELECT * FROM meeting_materials WHERE event_id=?", (number,))
    if not rows:
        raise ValueError("O evento ainda não tem materiais associados.")
    return rows[0]


def text_source(root, name, *, pdf=False):
    path = safe_path(root, name)
    if any(part.startswith(".") or part in SKIP for part in path.relative_to(root).parts):
        raise ValueError("Escolhe um ficheiro numa pasta de documentos do projeto.")
    types = TEXT_SOURCES | ({".pdf"} if pdf else set())
    if path.suffix.lower() not in types or not path.is_file():
        raise ValueError("Escolhe um ficheiro de texto ou de transcrição existente no projeto.")
    limit = 32 * 1024 * 1024 if path.suffix.lower() == ".pdf" else MAX_TEXT
    if path.stat().st_size > limit:
        raise ValueError("O ficheiro excede o limite de leitura para este formato.")
    return path


def read_source(root, name):
    path = text_source(root, name)
    with path.open("rb") as stream:
        content = stream.read(MAX_TEXT + 1)
    if len(content) > MAX_TEXT:
        raise ValueError("O ficheiro de texto excede 512 kB.")
    return content.decode("utf-8-sig", errors="replace")


def review_documents(root, payload):
    if (not isinstance(payload, list) or len(payload) > 10
            or not all(isinstance(name, str) and 0 < len(name.strip()) <= 500 for name in payload)):
        raise ValueError("Indica até 10 caminhos para documentos PDF, Markdown, TXT, VTT ou SRT.")
    return [text_source(root, name, pdf=True).relative_to(root).as_posix() for name in payload]


def transcript_lines(text, subtitle):
    timestamp = None
    for number, line in enumerate(text.splitlines(), 1):
        if match := TIMECODE.match(line):
            clock = match[1]
            timestamp = clock.replace(",", ".").split(".")[0]
            continue
        line = line.strip()
        if subtitle:
            if not line or line.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
                timestamp = None
            if timestamp is None or line.isdigit():
                continue
        if bracket := MARKED_TIME.match(line):
            timestamp, line = bracket[1], line[bracket.end():]
        line = re.sub(r"</?(?:v|i|b|u|c)(?: [^>]*|[.][^>]*)?>", "", line).strip()
        if line:
            yield number, timestamp, line


def transcript_sections(text, suffix):
    sections = defaultdict(list)
    for number, timestamp, line in transcript_lines(text, suffix in {".vtt", ".srt"}):
        line = line.lstrip("-• ")
        if not line:
            continue
        mark = MARKED_SECTION.match(line)
        if mark and mark[1].casefold() in {"decisão", "decisao", "decidimos"}:
            section = "Decisões"
        elif mark:
            section = "Tarefas e prazos"
        else:
            section = "Excertos da reunião"
        if len(sections[section]) < 12:
            location = timestamp or f"linha {number}"
            sections[section].append(f"- {location} · {line[:300]}")
    return sections


def render_lists(analysis, groups):
    lines = []
    for section in groups:
        entries = analysis[section]
        if entries:
            lines.append(section + "\n" + "\n".join(entries))
    return "\n\n".join(lines)


def render_analysis(title, analysis):
    sections = render_lists(analysis, ("Decisões", "Tarefas e prazos", "Excertos da reunião"))
    if not sections:
        return f"{title}\n\nA transcrição não contém texto que possa apresentar."
    return f"{title}\n\n{sections}"
