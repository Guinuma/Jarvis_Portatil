"""Pedidos locais de lembrete para o chat do MVP."""
import re
from datetime import datetime, timedelta

from .editor import normalize

REMINDER = re.compile(
    r"(?:jarvis[, ]+)?lembra-me daqui a ([0-9]{1,4}) (segundos?|minutos?|horas?) de (.+)"
)
COMBINED = re.compile(
    r"(?:jarvis[, ]+)?abre o meu projeto(?: no vs code)?,\s*"
    r"encontra as notas da ultima sessao\s+e\s+(?=lembra-me )"
)


def parse_reminder(text):
    normalized = normalize(text)
    clock = re.fullmatch(r"(?:jarvis[, ]+)?lembra-me as (\d{1,2})[:h](\d{2}) de (.+)", normalized)
    if clock:
        now = datetime.now()
        try:
            target = now.replace(hour=int(clock[1]), minute=int(clock[2]), second=0, microsecond=0)
        except ValueError:
            raise ValueError("Indica uma hora válida, como 18:30.") from None
        if target <= now:
            target += timedelta(days=1)
        return text[clock.start(3):].strip(), target.timestamp()

    timer = re.fullmatch(r"(?:jarvis[, ]+)?(?:cria|inicia) um temporizador (?:de|para) (\d{1,4}) (segundos?|minutos?|horas?)[.!?]?", normalized)
    match = REMINDER.fullmatch(normalized)
    if timer:
        text = f"Lembra-me daqui a {timer[1]} {timer[2]} de verificar o temporizador"
        match = REMINDER.fullmatch(normalize(text))
    if not match:
        return None
    quantity, unit, _ = match.groups()
    seconds = int(quantity) * {"s": 1, "m": 60, "h": 3600}[unit[0]]
    if not 1 <= seconds <= 86400:
        raise ValueError("Escolhe um intervalo entre 1 segundo e 24 horas.")
    return text[match.start(3):].strip(), datetime.now().timestamp() + seconds
