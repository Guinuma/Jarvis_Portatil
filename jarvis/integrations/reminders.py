"""Pedidos locais de lembrete para o chat do MVP."""
import re
from datetime import datetime, timedelta

from .editor import normalize

REMINDER = re.compile(
    r"(?:jarvis[, ]+)?lembra-me daqui a ([a-z0-9 ]{1,35}?) (segundos?|minutos?|horas?) de (.+)"
)
COMBINED = re.compile(
    r"(?:jarvis[, ]+)?abre o meu projeto(?: no vs code)?[,.;]\s*"
    r"encontr[ae] as notas da ultima sessao\s+e\s+(?=lembra-me )"
)


def quantity_value(text):
    words = dict(zip('zero um dois tres quatro cinco seis sete oito nove dez onze doze treze catorze quinze dezasseis dezassete dezoito dezanove'.split(), range(20)))
    words.update(uma=1, duas=2, vinte=20, trinta=30, quarenta=40, cinquenta=50,
                 sessenta=60, setenta=70, oitenta=80, noventa=90)
    if text.isdigit():
        return int(text)
    if text in words:
        return words[text]
    parts = text.split(' e ')
    if len(parts) == 2:
        first, last = (int(p) if p.isdigit() else words.get(p, -1) for p in parts)
        if 20 <= first <= 90 and first % 10 == 0 and 1 <= last <= 9:
            return first + last
    raise ValueError('Indica um intervalo como 45 minutos ou quarenta e cinco minutos.')


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

    timer = re.fullmatch(r"(?:jarvis[, ]+)?(?:cria|inicia) um temporizador (?:de|para) ([a-z0-9 ]{1,35}?) (segundos?|minutos?|horas?)[.!?]?", normalized)
    match = REMINDER.fullmatch(normalized)
    if timer:
        text = f"Lembra-me daqui a {timer[1]} {timer[2]} de verificar o temporizador"
        match = REMINDER.fullmatch(normalize(text))
    if not match:
        return None
    quantity, unit, _ = match.groups()
    seconds = quantity_value(quantity) * {"s": 1, "m": 60, "h": 3600}[unit[0]]
    if not 1 <= seconds <= 86400:
        raise ValueError("Escolhe um intervalo entre 1 segundo e 24 horas.")
    return text[match.start(3):].strip(), datetime.now().timestamp() + seconds
