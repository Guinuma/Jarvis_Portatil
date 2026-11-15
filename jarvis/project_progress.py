"""Mostrar o progresso registado num checklist Markdown autorizado."""
import re
from datetime import date

from .integrations.editor import resolve_project
from .integrations.project_files import safe_path

REQUEST = re.compile(
    r'(?:mostra (?:o )?)?progresso do projeto(?: "([^"]+)")?(?: na fase (\d{1,3}))?[.!]?', re.I
)
ITEM = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$")
PHASE = re.compile(r"^##\s+Fase\s+(\d+)\b", re.I)
DEADLINE = re.compile(r"\bprazo\s*[:=]?\s*(\d{4}-\d{2}-\d{2})\b", re.I)
FENCE = re.compile(r"^\s*(\x60{3,}|~{3,})(.*)$")


def progress_command(text, root):
    match = REQUEST.fullmatch(text)
    if not match:
        return None
    projects = resolve_project(match[1] or "", root)
    if len(projects) != 1:
        raise ValueError("Indica um projeto autorizado pelo nome ou caminho exato.")
    name, folder = projects[0]
    checklist = next(
        (path for filename in ("checklist.md", "README.md")
         if (path := safe_path(folder, filename)).is_file()), None
    )
    if checklist is None or checklist.stat().st_size > 512_000:
        raise ValueError("O projeto precisa de um checklist.md ou README.md com até 512 kB.")
    selected_phase = int(match[2]) if match[2] else None
    done, pending, deadlines = checklist_progress(checklist, selected_phase)
    if not done and not pending:
        return f"Não encontrei tarefas Markdown em {checklist.name} para o pedido indicado."
    scope = f" · Fase {selected_phase}" if selected_phase is not None else ""
    lines = [f"{name}{scope} · {len(done)} marcadas e {len(pending)} em aberto",
             f"Fonte — {checklist.name}"]
    for heading, items in (("Marcadas", done), ("Em aberto", pending)):
        if items:
            lines.extend(["", heading])
            lines.extend(f"- Linha {number} · {title[:240]}" for number, title in items[:5])
            if len(items) > 5:
                lines.append(f"Mais {len(items) - 5} no ficheiro de origem.")
    lines.extend(["", "Prazos nas tarefas em aberto"])
    if not deadlines:
        lines.append("O checklist não indica prazos no formato AAAA-MM-DD.")
    for due, (number, title) in sorted(deadlines)[:5]:
        label = " · em atraso" if due < date.today() else ""
        lines.append(f"- {due:%d/%m/%Y}{label} · linha {number} · {title[:200]}")
    return "\n".join(lines)


def checklist_progress(path, selected_phase):
    current = None
    fence = None
    done, pending, deadlines = [], [], []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if marker := FENCE.match(line):
            chars, tail = marker.groups()
            if fence is None:
                fence = chars
            elif chars[0] == fence[0] and len(chars) >= len(fence) and not tail.strip():
                fence = None
            continue
        if fence:
            continue
        if phase := PHASE.match(line):
            current = int(phase[1])
        elif re.match(r"^#{1,2}\s", line):
            current = None
        if selected_phase is not None and current != selected_phase:
            continue
        item = ITEM.match(line)
        if not item:
            continue
        checked, title = item.groups()
        entry = (number, title.split(" **", 1)[0])
        (pending if checked == " " else done).append(entry)
        if checked == " " and (deadline := DEADLINE.search(title)):
            try:
                due = date.fromisoformat(deadline[1])
            except ValueError:
                continue
            deadlines.append((due, entry))
    return done, pending, deadlines
