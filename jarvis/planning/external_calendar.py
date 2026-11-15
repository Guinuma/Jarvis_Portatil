"""Consultar os eventos do dia em calendários Google autorizados por perfil."""
import json
import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit

from jarvis.integrations.http_client import ServiceError, remote_json

QUERY = re.compile(
    r'(?:jarvis[, ]+)?(?:mostra|consulta) (?:a )?agenda (?:externa|google)'
    r'(?: "([a-zA-Z0-9_-]{1,40})")?(?: (?:de )?(hoje|amanhã|\d{4}-\d{2}-\d{2}))?[.!?]?', re.I,
)
LIST = re.compile(r'(?:jarvis[, ]+)?mostra (?:os )?calendários externos[.!?]?', re.I)
BASE = "https://www.googleapis.com/calendar/v3/calendars/"


def calendars(memory):
    filename = os.environ.get("JARVIS_CALENDARS_FILE")
    if not filename:
        return {}
    try:
        with Path(filename).expanduser().open("rb") as stream:
            data = stream.read(64001)
        if len(data) > 64000:
            raise ValueError
        profile = json.loads(data.decode("utf-8-sig"))["perfis"].get(memory.path.stem, [])
        if not isinstance(profile, list) or len(profile) > 12:
            raise ValueError
        result = {}
        for entry in profile:
            name = entry["id"].casefold()
            calendar, token = entry["calendario"], entry["token_env"]
            if (name in result or not re.fullmatch(r"[a-z0-9_-]{1,40}", name)
                    or not isinstance(calendar, str) or not re.fullmatch(r"[A-Za-z0-9@._+%#-]{1,300}", calendar)
                    or not re.fullmatch(r"JARVIS_CALENDAR_TOKEN_[A-Z0-9_]{1,40}", token)):
                raise ValueError
            result[name] = (calendar, token)
        return result
    except (ValueError, OSError, TypeError, AttributeError, KeyError) as error:
        raise ValueError("Revê a configuração dos calendários externos do perfil.") from error


def calendar_command(text, memory):
    if LIST.fullmatch(text):
        allowed = calendars(memory)
        return reply("Calendários externos · " + ", ".join(sorted(allowed)) if allowed else "Sem calendários externos configurados.")
    match = QUERY.fullmatch(text)
    if not match:
        return None
    name, when = match.groups()
    allowed = calendars(memory)
    if not allowed:
        raise ValueError("Configura JARVIS_CALENDARS_FILE para consultar um calendário Google autorizado.")
    if name is None and len(allowed) > 1:
        return reply("Indica o calendário externo a consultar · " + ", ".join(sorted(allowed)) + ".")
    label = name.casefold() if name else next(iter(allowed))
    if label not in allowed:
        raise ValueError("Esse calendário externo não está autorizado neste perfil.")
    value = (when or "hoje").casefold()
    today = date.today()
    day = today if value == "hoje" else today + timedelta(days=1) if value == "amanhã" else date.fromisoformat(value)
    if not 2 <= day.toordinal() < date.max.toordinal():
        raise ValueError("Indica uma data dentro do intervalo suportado.")
    identifier, token_env = allowed[label]
    token = os.environ.get(token_env, "")
    if not 1 <= len(token) <= 8192 or any(not 33 <= ord(char) <= 126 for char in token):
        raise ValueError(f"Configura um token OAuth de leitura em {token_env} e reinicia o JARVIS.")
    result, more = events_for_day(identifier, token, day)
    return format_agenda(label, day, result, more)


def events_for_day(identifier, token, day):
    start = datetime.combine(day, time.min).astimezone()
    end = datetime.combine(day + timedelta(days=1), time.min).astimezone()
    params = {
        "timeMin": start.isoformat(timespec="seconds"),
        "timeMax": end.isoformat(timespec="seconds"),
        "singleEvents": "true", "showDeleted": "false", "orderBy": "startTime", "maxResults": 40,
        "fields": "items(summary,start,end,status,htmlLink),nextPageToken",
    }
    url = BASE + quote(identifier, safe="") + "/events"
    events = []
    for _ in range(4):
        data = remote_json(url, params, "Google Calendar", bearer=token)
        items = data.get("items") or []
        if not isinstance(items, list):
            raise ServiceError("O Google Calendar devolveu uma lista inválida.")
        events.extend(event for event in items if isinstance(event, dict) and event.get("status") != "cancelled")
        next_page = data.get("nextPageToken")
        if not next_page:
            return events, False
        if not isinstance(next_page, str) or len(next_page) > 8192 or next_page == params.get("pageToken"):
            raise ServiceError("A paginação do Google Calendar devolveu um resultado inválido.")
        params["pageToken"] = next_page
    return events, True


def event_time(data):
    if not isinstance(data, dict):
        return ""
    for key in ("dateTime", "date"):
        timestamp = data.get(key)
        if not isinstance(timestamp, str):
            continue
        try:
            if key == "date":
                return f"{date.fromisoformat(timestamp):%d/%m}"
            value = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return f"{value.astimezone():%d/%m %H:%M}" if value.tzinfo else timestamp[:26]
        except (ValueError, OSError, OverflowError):
            continue
    return ""


def event_link(value):
    if not isinstance(value, str) or len(value) > 1800 or any(char.isspace() or char == "\\" for char in value):
        return None
    try:
        event = urlsplit(value)
        if event.scheme == "https" and event.netloc in {"www.google.com", "calendar.google.com"} and event.path.startswith("/calendar"):
            return value
    except ValueError:
        pass
    return None


def format_agenda(label, day, events, more):
    lines = [f"Google Calendar · {label} · {day:%d/%m/%Y}"]
    links = []
    for event in events[:30]:
        start = event_time(event.get("start"))
        end = event_time(event.get("end"))
        clock = "Dia inteiro" if isinstance(event.get("start"), dict) and event["start"].get("date") else "–".join(filter(None, (start, end)))
        title = event.get("summary")
        title = " ".join(title.split())[:180] if isinstance(title, str) else ""
        title = title or "Compromisso sem título disponível"
        lines.append(f"- {clock or 'Hora indisponível'} · {title}")
        if url := event_link(event.get("htmlLink")):
            links.append({"label": title, "url": url})
    if not events:
        lines.append("Sem compromissos disponíveis neste dia.")
    if more or len(events) > 30:
        lines.append("A lista foi limitada a 30 compromissos.")
    return reply("\n".join(lines), links)


def reply(text, links=()):
    return {"reply": text, "links": list(links), "transient": True, "provider": "Google Calendar"}
