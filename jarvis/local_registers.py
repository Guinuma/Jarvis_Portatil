"""Inventário, despesas e catálogo de recibos guardados por perfil."""
import re
from datetime import date

from .integrations.compare import MAX_FILE
from .integrations.editor import normalize
from .integrations.project_files import safe_path

QUOTED = r'"([^"\r\n]{1,160})"'
DAY = r'(\d{4}-\d{2}-\d{2})'
PERIOD = rf'(?: de {DAY} a {DAY})?'
INVENTORY_ADD = re.compile(rf'regista no inventário {QUOTED} em {QUOTED}(?: quantidade (\d{{1,6}}))?[.!]?', re.I)
INVENTORY_FIND = re.compile(rf'(?:consulta|mostra) o inventário(?: (nome|local) {QUOTED})?[.!]?', re.I)
EXPENSE_ADD = re.compile(rf'regista despesa (\d{{1,9}}(?:[.,]\d{{1,2}})?) (?:euros?|€) em {QUOTED} na categoria {QUOTED} em {DAY}[.!]?', re.I)
EXPENSES = re.compile(rf'mostra despesas{PERIOD}(?: na categoria {QUOTED})?[.!]?', re.I)
RECEIPT_ADD = re.compile(rf'regista recibo "([^"\r\n]{{1,500}})" de {QUOTED} em {DAY}[.!]?', re.I)
RECEIPTS = re.compile(rf'(?:procura|mostra) recibos{PERIOD}(?: de {QUOTED})?[.!]?', re.I)
VOID_EXPENSE = re.compile(r'anula (?:a )?despesa (\d{1,18})[.!]?', re.I)


def register_command(text, memory, root, sources):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := INVENTORY_ADD.fullmatch(command):
        return save_inventory(memory, *match.groups())
    if match := INVENTORY_FIND.fullmatch(command):
        return show_inventory(memory, *match.groups())
    if match := EXPENSE_ADD.fullmatch(command):
        return save_expense(memory, *match.groups())
    if match := EXPENSES.fullmatch(command):
        return show_expenses(memory, *match.groups())
    if match := VOID_EXPENSE.fullmatch(command):
        row = memory.execute(
            "UPDATE expenses SET void=1 WHERE id=? AND void=0 RETURNING id", (int(match[1]),),
        )
        return f"Despesa {match[1]} anulada." if row else "Não encontrei essa despesa ativa."
    if match := RECEIPT_ADD.fullmatch(command):
        return save_receipt(memory, root, *match.groups())
    if match := RECEIPTS.fullmatch(command):
        return show_receipts(memory, root, sources, *match.groups())
    return None


def label(value):
    value = value.strip()
    if not value or not normalize(value):
        raise ValueError("Indica um nome, local ou categoria.")
    return value


def saved_day(value):
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise ValueError("Indica uma data válida no formato AAAA-MM-DD.") from error


def date_range(start, end):
    if start is None:
        today = date.today()
        return today.replace(day=1).isoformat(), today.isoformat()
    lower, upper = saved_day(start), saved_day(end)
    if lower > upper:
        raise ValueError("A data inicial tem de ser anterior ou igual à data final.")
    return lower, upper


def save_inventory(memory, name, place, quantity):
    name, place = label(name), label(place)
    units = int(quantity) if quantity else 1
    if units < 1:
        raise ValueError("Indica uma quantidade positiva.")
    memory.execute(
        """INSERT INTO home_inventory (name_key, place_key, name, place, units) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(name_key, place_key) DO UPDATE
           SET name=excluded.name, place=excluded.place, units=excluded.units""",
        (normalize(name), normalize(place), name, place, units),
    )
    return f"Inventário atualizado · {name} · {place} · quantidade {units}."


def show_inventory(memory, field, value):
    query = normalize(label(value)) if value is not None else ""
    rows = memory.execute(
        """SELECT name, place, units FROM home_inventory
           WHERE CASE ? WHEN 'local' THEN instr(place_key, ?) ELSE instr(name_key, ?) END > 0
           ORDER BY name_key, place_key LIMIT 21""",
        ((field or "nome").lower(), query, query),
    )
    if not rows:
        return "Não encontrei itens no inventário para essa consulta."
    lines = [f"{row['name']} · {row['place']} · quantidade {row['units']}" for row in rows[:20]]
    if len(rows) > 20:
        lines.append("Há mais resultados. Pesquisa por nome ou local para limitar a lista.")
    return "\n".join(lines)


def amount_text(cents):
    whole, fraction = divmod(cents, 100)
    return f"{whole},{fraction:02d} €"


def save_expense(memory, amount, trader, category, day):
    whole, _, fraction = amount.replace(",", ".").partition(".")
    cents = int(whole) * 100 + int(fraction.ljust(2, "0"))
    if not cents:
        raise ValueError("Indica um valor em euros superior a zero.")
    trader, category, day = label(trader), label(category), saved_day(day)
    row = memory.execute(
        """INSERT INTO expenses (trader, category, category_key, cents, day)
           VALUES (?, ?, ?, ?, ?) RETURNING id""",
        (trader, category, normalize(category), cents, day),
    )[0]
    return f"Despesa {row['id']} registada · {trader} · {category} · {amount_text(cents)} · {day}."


def show_expenses(memory, start, end, category):
    lower, upper = date_range(start, end)
    key = normalize(label(category)) if category is not None else None
    rows = memory.execute(
        """SELECT max(category) AS category, sum(cents) AS total, count(*) AS quantity FROM expenses
           WHERE void=0 AND day BETWEEN ? AND ? AND (? IS NULL OR category_key=?)
           GROUP BY category_key ORDER BY total DESC, category_key""",
        (lower, upper, key, key),
    )
    if not rows:
        return f"Sem despesas registadas de {lower} a {upper} para essa consulta."
    total = amount_text(sum(row["total"] for row in rows))
    lines = [f"Despesas de {lower} a {upper} · total {total}"]
    lines.extend(f"{row['category']} · {amount_text(row['total'])} · {row['quantity']} registo(s)" for row in rows[:20])
    if len(rows) > 20:
        lines.append("O total inclui todas as categorias. A lista mostra as 20 com maior valor.")
    return "\n".join(lines)


def save_receipt(memory, root, name, trader, day):
    path = safe_path(root, name)
    if not available_receipt(path):
        raise ValueError("Indica um recibo PDF existente no projeto com até 32 MB.")
    relative = path.relative_to(root).as_posix()
    trader, day = label(trader), saved_day(day)
    row = memory.execute(
        """INSERT INTO receipts (root, path, trader, trader_key, day) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(root, path) DO UPDATE
           SET trader=excluded.trader, trader_key=excluded.trader_key, day=excluded.day RETURNING id""",
        (str(root), relative, trader, normalize(trader), day),
    )[0]
    return f"Recibo {row['id']} catalogado · {trader} · {day} · {relative}."


def show_receipts(memory, root, sources, start, end, trader):
    lower, upper = date_range(start, end) if start else ("0001-01-01", "9999-12-31")
    key = normalize(label(trader)) if trader is not None else ""
    rows = memory.execute(
        """SELECT path, trader, day FROM receipts WHERE root=? AND day BETWEEN ? AND ?
           AND instr(trader_key, ?) > 0 ORDER BY day DESC, id DESC LIMIT 21""", (str(root), lower, upper, key),
    )
    if not rows:
        return "Não encontrei recibos para essa consulta."
    lines = []
    for row in rows[:20]:
        try:
            path = safe_path(root, row["path"])
            available = available_receipt(path)
        except (OSError, ValueError, RuntimeError):
            available = False
        if available:
            sources.append((path.relative_to(root).as_posix(), None))
        suffix = "" if available else " · ficheiro indisponível"
        lines.append(f"{row['day']} · {row['trader']} · {row['path']}{suffix}")
    if len(rows) > 20:
        lines.append("Há mais resultados. Limita a pesquisa por data ou comerciante.")
    return "\n".join(lines)


def available_receipt(path):
    return path.suffix.lower() == ".pdf" and path.is_file() and path.stat().st_size <= MAX_FILE
