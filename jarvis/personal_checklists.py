"""Personal checklists shared by chat and the Windows widget."""
import json
import re

CREATE = re.compile(r'(?:cria|criar) (?:uma )?(?:lista(?: pessoal)?|checklist) (.+)', re.I | re.S)
TITLE_ITEMS = re.compile(r'(?:"([^"]+)"(?:\s*:\s*|\s+com\s+)|(.+?)(?:\s*:\s*|\s+com\s+))(.+)', re.I | re.S)
SHOW = re.compile(r'(?:mostra|lista) (?:as )?(?:minhas )?(?:listas pessoais|checklists pessoais)[.!]?', re.I)
SELECTION = "personal_checklist_widget"


def personal_checklist_command(text, memory):
    if SHOW.fullmatch(text):
        lists = list_checklists(memory)
        if not lists:
            return 'Ainda não tens listas pessoais. Experimenta «Cria uma lista "Ensaio": levar cabos, carregar a interface».'
        return "Listas pessoais\n" + "\n".join(f"- {entry['title']}" for entry in lists)
    match = CREATE.fullmatch(text)
    if not match:
        return None
    payload = TITLE_ITEMS.fullmatch(match[1])
    if not payload:
        raise ValueError('Indica o nome e os itens. Por exemplo, «Cria uma lista "Ensaio": levar cabos, carregar a interface».')
    title = (payload[1] or payload[2]).strip()
    raw_items = payload[3].strip()
    if "\n" in raw_items or ";" in raw_items:
        parts = re.split(r"[;\n]", raw_items)
    else:
        parts = raw_items.split(",")
        parts[-1:] = re.split(r"\s+e\s+", parts[-1], flags=re.I)
    labels = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", part).strip() for part in parts]
    labels = [label for label in labels if label]
    if not 1 <= len(title) <= 100 or not 1 <= len(labels) <= 30 or any(len(label) > 200 for label in labels):
        raise ValueError("Usa um nome até 100 caracteres e até 30 itens de 200 caracteres cada.")
    items = [{"label": label, "done": 0} for label in labels]
    memory.execute("INSERT INTO personal_checklists(title, items) VALUES (?, ?)", (title, json.dumps(items, ensure_ascii=False)))
    return f'Criei a lista «{title}» com {len(items)} {"item" if len(items) == 1 else "itens"}. Podes escolhê-la no widget Checklist.'


def list_checklists(memory):
    return memory.execute("SELECT id, title FROM personal_checklists ORDER BY id DESC")


def checklist_items(memory, list_id):
    rows = memory.execute("SELECT items FROM personal_checklists WHERE id = ?", (list_id,))
    return json.loads(rows[0]["items"]) if rows else []


def set_item(memory, list_id, index, done):
    memory.execute(
        "UPDATE personal_checklists SET items = json_set(items, ?, ?) "
        "WHERE id = ? AND ? >= 0 AND ? < json_array_length(items)",
        (f"$[{index}].done", int(done), list_id, index, index),
    )


def widget_selection(memory):
    matches = memory.execute("SELECT value FROM settings WHERE name = ?", (SELECTION,))
    return int(matches[0]["value"]) if matches else None


def save_widget_selection(memory, list_id):
    memory.execute(
        "INSERT INTO settings(name, value) VALUES (?, ?) "
        "ON CONFLICT(name) DO UPDATE SET value = excluded.value",
        (SELECTION, str(list_id)),
    )
