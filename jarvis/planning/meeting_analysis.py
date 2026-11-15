"""Identificar propostas de decisões e tarefas em transcrições autorizadas."""
import hashlib
import json
import re

from jarvis.education.reasoning import LocalModelError, ask_local, records_schema
from jarvis.planning.meetings import event_row, materials_row, read_source, result, transcript_lines

REQUEST = re.compile(
    r'identifica decisões e tarefas do evento (\d{1,18})(?: entre (\d{2}:\d{2}:\d{2}) e (\d{2}:\d{2}:\d{2}))?[.!]?',
    re.I,
)


def clock_seconds(value):
    pieces = [int(part) for part in value.replace(",", ".").split(".", 1)[0].split(":")]
    if len(pieces) == 2:
        pieces.insert(0, 0)
    hours, minutes, seconds = pieces
    if minutes >= 60 or seconds >= 60:
        raise ValueError("Indica marcas de tempo válidas no formato HH:MM:SS.")
    return (hours * 60 + minutes) * 60 + seconds


def cues_from(text, subtitle):
    excerpts = []
    for number, stamp, line in transcript_lines(text, subtitle):
        excerpts.append({"número": len(excerpts) + 1, "marca": stamp or f"linha {number}",
                         "texto": line[:400], "segundos": clock_seconds(stamp) if stamp else None})
    return excerpts

def choose_cues(cues, start, end):
    if start:
        lower, upper = clock_seconds(start), clock_seconds(end)
        if lower >= upper:
            raise ValueError("A marca inicial deve ser anterior à final.")
        cues = [cue for cue in cues if cue["segundos"] is not None and lower <= cue["segundos"] < upper]
    chosen, total = [], 0
    for cue in cues:
        total += len(cue["texto"])
        if len(chosen) >= 90 or total > 12_000:
            break
        chosen.append(cue)
    if not chosen:
        raise ValueError("A transcrição não tem excertos de texto no intervalo indicado.")
    return chosen, len(chosen) < len(cues)


def infer_items(cues):
    schema = records_schema("itens", {
        "tipo": {"type": "string", "enum": ["decisão", "tarefa"]},
        "texto": {"type": "string"},
        "excerto": {"type": "integer"},
        "responsável": {"type": "string"},
        "prazo": {"type": "string"},
    })
    answer = ask_local(
        "Identifica até dez decisões tomadas ou tarefas acordadas. Inclui o número de um excerto que as sustenta. "
        "Preenche responsável e prazo só quando essas expressões aparecem literalmente no excerto escolhido. "
        "Se faltarem dados, deixa o campo vazio. Se não houver decisões nem tarefas, devolve a lista vazia.",
        [{key: cue[key] for key in ("número", "marca", "texto")} for cue in cues],
        limit=1500, schema=schema,
    )
    items = answer.get("itens") if isinstance(answer, dict) else None
    if not isinstance(items, list) or len(items) > 10:
        raise LocalModelError("O modelo local não devolveu uma lista de decisões e tarefas válida.")
    quoted = {cue["número"]: cue for cue in cues}
    final = []
    for item in items:
        if (not isinstance(item, dict) or type(item.get("excerto")) is not int or item["excerto"] not in quoted
                or item.get("tipo") not in ("decisão", "tarefa") or not isinstance(item.get("texto"), str)
                or not item["texto"].strip()):
            raise LocalModelError("A análise apontou para um excerto inexistente ou incluiu um item inválido.")
        actual = quoted[item["excerto"]]
        fields = {}
        for field in ("responsável", "prazo"):
            value = item.get(field)
            if isinstance(value, str) and 0 < len(value.strip()) <= 100 and value.strip().casefold() in actual["texto"].casefold():
                fields[field] = value.strip()
        final.append({"kind": item["tipo"], "text": " ".join(item["texto"].split())[:300],
                      "mark": actual["marca"], "quote": actual["texto"], **fields})
    return final


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_item(item, include_quote):
    details = " · ".join(f"{label}: {item[label]}" for label in ("responsável", "prazo") if item.get(label))
    quote = f"\n  Excerto — «{item['quote']}»" if include_quote else ""
    return f"- {item['mark']} · {item['kind'].capitalize()} · {item['text']}" + (f" · {details}" if details else "") + quote


def meeting_analysis_command(text, memory, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    match = REQUEST.fullmatch(command)
    if not match:
        return None
    number = int(match[1])
    event = event_row(memory, number)
    record = materials_row(memory, number)
    name = record["transcript"]
    if not name:
        raise ValueError("Associa ou grava primeiro uma transcrição para este evento.")
    source = read_source(root, name)
    excerpts, limited = choose_cues(cues_from(source, name.casefold().endswith((".vtt", ".srt"))), match[2], match[3])
    insights = infer_items(excerpts)
    if digest(read_source(root, name)) != digest(source):
        raise ValueError("A transcrição mudou durante a análise. Repete o pedido com a nova versão.")
    scope = f"{match[2]}–{match[3]}" if match[2] else "início"
    saved = memory.execute(
        """INSERT INTO meeting_insights (event_id, path, digest, scope, items)
           SELECT event_id, transcript, ?, ?, ? FROM meeting_materials WHERE event_id=? AND transcript=?
           ON CONFLICT(event_id, digest, scope) DO UPDATE SET path=excluded.path, items=excluded.items
           RETURNING event_id""", (digest(source), scope, json.dumps(insights, ensure_ascii=False), number, name),
    )
    if not saved:
        raise ValueError("A transcrição associada mudou durante a análise.")
    lines = [f"{event['title']} · análise orientativa", f"Intervalo analisado — {excerpts[0]['marca']} a {excerpts[-1]['marca']}"]
    if limited:
        lines.append("O intervalo foi limitado. Indica outro intervalo para analisar os excertos seguintes.")
    lines.extend(render_item(item, include_quote=True) for item in insights)
    if not insights:
        lines.append("O modelo não identificou decisões ou tarefas neste intervalo.")
    return result("\n".join(lines), [name])


def inferred_followup(memory, event_id, name, transcript):
    rows = memory.execute(
        """SELECT items FROM meeting_insights WHERE event_id=? AND path=? AND digest=?
           ORDER BY rowid LIMIT 12""", (event_id, name, digest(transcript)),
    )
    proposals = dict.fromkeys(render_item(item, include_quote=False)
                              for row in rows for item in json.loads(row["items"]))
    if not proposals:
        return ""
    return "Sugestões a rever com a transcrição\n" + "\n".join(list(proposals)[:12])
