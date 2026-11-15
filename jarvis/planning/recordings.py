"""Guardar blocos transcritos e publicar a legenda associada a um evento."""
import base64
import binascii
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from jarvis.integrations.project_files import safe_path
from jarvis.integrations.voice import transcribe_segments
from jarvis.planning.meetings import event_row

SESSION = re.compile(r"[0-9a-f]{32}")
MAX_CHUNKS = 48
MAX_MS = 30 * 60 * 1000
BODY_LIMIT = 12 * 1024 * 1024


def recording_request(memory, root, data):
    action = data["action"]
    if action == "list":
        rows = memory.execute(
            """SELECT r.id, r.event_id, a.title, r.status, r.path, count(s.number) AS chunks
               FROM meeting_recordings AS r JOIN agenda AS a ON a.id=r.event_id
               LEFT JOIN meeting_segments AS s ON s.recording_id=r.id
               GROUP BY r.id ORDER BY r.rowid DESC LIMIT 12"""
        )
        return {"recordings": rows}
    if action == "start":
        return start_recording(memory, data)
    identifier = data["id"]
    if not isinstance(identifier, str) or not SESSION.fullmatch(identifier):
        raise ValueError("Identificador de gravação inválido.")
    row = recording_row(memory, identifier)
    if action == "chunk":
        return add_chunk(memory, row, data)
    if action == "finish":
        return finish_recording(memory, root, row, data["chunks"])
    raise ValueError("Ação de gravação desconhecida.")


def start_recording(memory, data):
    event_id = data["event"]
    if data.get("consent") is not True:
        raise ValueError("Confirma que obtiveste consentimento antes de começar.")
    if type(event_id) is not int or not 0 < event_id <= 9007199254740991:
        raise ValueError("Indica um número válido de evento.")
    event = event_row(memory, event_id)
    identifier = uuid4().hex
    rows = memory.execute(
        """INSERT INTO meeting_recordings (id, event_id) VALUES (?, ?)
           ON CONFLICT DO NOTHING RETURNING id""", (identifier, event_id),
    )
    if not rows:
        raise ValueError("Este evento já tem uma gravação aberta. Guarda os blocos no painel primeiro.")
    return {"id": identifier, "event": event_id, "title": event["title"]}


def recording_row(memory, identifier):
    rows = memory.execute("SELECT * FROM meeting_recordings WHERE id=?", (identifier,))
    if not rows:
        raise ValueError("Não encontrei esta gravação no perfil atual.")
    return rows[0]


def add_chunk(memory, row, data):
    number, offset = data["number"], data["offset"]
    if type(number) is not int or not 1 <= number <= MAX_CHUNKS or type(offset) is not int or not 0 <= offset < MAX_MS:
        raise ValueError("Bloco de gravação inválido.")
    if not isinstance(data["audio"], str):
        raise ValueError("O bloco de áudio está inválido.")
    try:
        audio = base64.b64decode(data["audio"], validate=True)
    except binascii.Error as error:
        raise ValueError("O bloco de áudio está inválido.") from error
    digest = hashlib.sha256(audio).hexdigest()
    if chunk_matches(memory, row["id"], number, offset, digest):
        return {"number": number}
    if row["status"] != "a gravar":
        raise ValueError("Esta gravação já foi fechada.")
    previous = memory.execute(
        "SELECT count(*) AS total, max(offset) AS offset FROM meeting_segments WHERE recording_id=?", (row["id"],),
    )[0]
    if previous["total"] != number - 1 or (previous["offset"] is not None and offset <= previous["offset"]):
        raise ValueError("Envia os blocos por ordem e com as marcas temporais da gravação.")
    segments = transcribe_segments(audio)
    inserted = memory.execute(
        """INSERT INTO meeting_segments (recording_id, number, offset, digest, cues)
           SELECT id, ?, ?, ?, ? FROM meeting_recordings WHERE id=? AND status='a gravar'
           ON CONFLICT(recording_id, number) DO NOTHING RETURNING number""",
        (number, offset, digest, json.dumps(segments, ensure_ascii=False), row["id"]),
    )
    if not inserted and not chunk_matches(memory, row["id"], number, offset, digest):
        raise ValueError("A gravação mudou antes de guardar este bloco.")
    return {"number": number}


def chunk_matches(memory, identifier, number, offset, digest):
    rows = memory.execute(
        "SELECT offset, digest FROM meeting_segments WHERE recording_id=? AND number=?", (identifier, number),
    )
    if rows and (rows[0]["offset"], rows[0]["digest"]) != (offset, digest):
        raise ValueError("Esse número já pertence a outro bloco de áudio.")
    return bool(rows)


def finish_recording(memory, root, row, count):
    if type(count) is not int or not 0 <= count <= MAX_CHUNKS:
        raise ValueError("Número de blocos inválido.")
    identifier = row["id"]
    if row["status"] == "concluída":
        return {"path": row["path"]}
    sealed = memory.execute(
        """UPDATE meeting_recordings SET status='a fechar'
           WHERE id=? AND status IN ('a gravar','a fechar')
             AND (SELECT count(*) FROM meeting_segments WHERE recording_id=?)=?
           RETURNING event_id""", (identifier, identifier, count),
    )
    if not sealed:
        final = recording_row(memory, identifier)
        if final["status"] == "concluída":
            return {"path": final["path"]}
        raise ValueError("Ainda há blocos por guardar. Atualiza o estado da gravação.")
    event_id = sealed[0]["event_id"]
    rows = memory.execute(
        "SELECT offset, cues FROM meeting_segments WHERE recording_id=? ORDER BY number", (identifier,),
    )
    cues = cue_lines(rows)
    path = None
    if cues:
        directory = safe_path(root, "reunioes")
        directory.mkdir(exist_ok=True)
        target = safe_path(root, f"reunioes/evento-{event_id}-{identifier}.vtt")
        publish_transcript(target, ("WEBVTT\n\n" + "\n\n".join(cues) + "\n").encode("utf-8"))
        path = target.relative_to(root).as_posix()
        memory.execute(
            """INSERT INTO meeting_materials (event_id, transcript)
               SELECT event_id, ? FROM meeting_recordings WHERE id=? AND status='a fechar'
               ON CONFLICT(event_id) DO UPDATE SET transcript=excluded.transcript, followup=''""", (path, identifier),
        )
    memory.execute(
        "UPDATE meeting_recordings SET status='concluída', path=? WHERE id=? AND status='a fechar'", (path, identifier),
    )
    return {"path": path}


def cue_lines(rows):
    lines = []
    last_end = 0
    for row in rows:
        for cue in json.loads(row["cues"]):
            start = max(last_end, row["offset"] + cue["start"])
            end = max(start + 1, row["offset"] + cue["end"])
            text = " ".join(cue["text"].split()).replace("-->", "→")
            if text:
                lines.append(f"{vtt_time(start)} --> {vtt_time(end)}\n{text}")
                last_end = end
    return lines


def vtt_time(milliseconds):
    seconds, mark = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{mark:03}"


def publish_transcript(target, contents):
    if target.is_symlink():
        raise ValueError("O destino da transcrição não é um ficheiro autorizado.")
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".vtt", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(contents)
    try:
        try:
            os.link(temporary, target)
        except FileExistsError as error:
            if target.stat().st_size != len(contents) or target.read_bytes() != contents:
                raise ValueError("Já existe outro ficheiro com o nome da transcrição.") from error
    finally:
        temporary.unlink(missing_ok=True)
