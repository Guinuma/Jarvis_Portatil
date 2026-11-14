"""Pedidos locais de lembrete para o chat do MVP."""
import re

from .editor import normalize

REMINDER = re.compile(
    r"(?:jarvis[, ]+)?lembra-me daqui a ([0-9]{1,4}) (segundos?|minutos?|horas?) de (.+)"
)
COMBINED = re.compile(
    r"(?:jarvis[, ]+)?abre o meu projeto(?: no vs code)?,\s*"
    r"encontra as notas da ultima sessao\s+e\s+(?=lembra-me )"
)


def parse_reminder(text):
    match = REMINDER.fullmatch(normalize(text))
    if not match:
        return None
    quantity, unit, _ = match.groups()
    seconds = int(quantity) * {"s": 1, "m": 60, "h": 3600}[unit[0]]
    if not 1 <= seconds <= 86400:
        raise ValueError("Escolhe um intervalo entre 1 segundo e 24 horas.")
    return text[match.start(3):].strip(), seconds
