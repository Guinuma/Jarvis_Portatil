"""Pesquisar na web e consultar previsões com APIs explícitas."""
import os
import re
from datetime import date, datetime, time, timedelta
from math import isfinite
from urllib.parse import urlencode, urlsplit

from jarvis.integrations.editor import normalize
from jarvis.integrations.html_text import PlainHTML
from jarvis.integrations.http_client import ServiceError, public_link, remote_json

SEARCH = re.compile(r'(?:procura|pesquisa) (na web|notícias sobre) "([^"\r\n]{1,600})"[.!]?', re.I)
WEATHER = re.compile(
    r'(?:meteorologia|tempo) (?:em|para) (?:"([^"\r\n]{2,100})"|local (\d{1,12}))'
    r'(?: (agora|hoje|amanhã|\d{4}-\d{2}-\d{2}))?(?: às (\d{2}:\d{2}))?[.!]?', re.I,
)
BRAVE = "https://api.search.brave.com/res/v1/"
GEO = "https://geocoding-api.open-meteo.com/v1/"
FORECAST = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = "temperature_2m,weather_code,wind_speed_10m"
HOURLY_FIELDS = CURRENT_FIELDS + ",precipitation_probability"
DAILY_FIELDS = "temperature_2m_min,temperature_2m_max,weather_code,precipitation_probability_max,wind_speed_10m_max"
CODES = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado", 3: "encoberto",
    45: "nevoeiro", 48: "nevoeiro com geada", 51: "chuvisco fraco", 53: "chuvisco moderado",
    55: "chuvisco intenso", 56: "chuvisco gelado fraco", 57: "chuvisco gelado intenso",
    61: "chuva fraca", 63: "chuva moderada", 65: "chuva forte", 66: "chuva gelada fraca",
    67: "chuva gelada forte", 71: "neve fraca", 73: "neve moderada", 75: "neve forte",
    77: "grãos de neve", 80: "aguaceiros fracos", 81: "aguaceiros moderados", 82: "aguaceiros fortes",
    85: "aguaceiros de neve fracos", 86: "aguaceiros de neve fortes", 95: "trovoada",
    96: "trovoada com granizo fraco", 99: "trovoada com granizo forte",
}


def clean_text(value, limit):
    if not isinstance(value, str):
        return ""
    parser = PlainHTML()
    try:
        parser.feed(value[:5000])
        parser.close()
    except (AssertionError, ValueError):
        return " ".join(value.split())[:limit]
    return " ".join("".join(parser.parts).split())[:limit]


def research_command(text):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := SEARCH.fullmatch(command):
        return search_web(match[2], normalize(match[1]) != "na web")
    if match := WEATHER.fullmatch(command):
        return weather(*match.groups())
    return None


def search_web(query, news):
    query = query.strip()
    chars, words = (400, 50) if news else (600, 75)
    if not query or len(query) > chars or len(query.split()) > words:
        raise ValueError(f"Indica uma pesquisa com até {chars} caracteres e {words} palavras.")
    token = os.environ.get("JARVIS_BRAVE_SEARCH_KEY", "").strip()
    if not token:
        raise ValueError("Configura JARVIS_BRAVE_SEARCH_KEY no ambiente do JARVIS para pesquisar com a Brave.")
    params = {"q": query, "count": 8, "country": "PT", "search_lang": "pt", "safesearch": "moderate"}
    if news:
        params["freshness"] = "pm"
    data = remote_json(BRAVE + ("news/search" if news else "web/search"), params, "Brave Search", token)
    if news:
        results = data.get("results") or []
    else:
        web = data.get("web")
        results = web.get("results") or [] if isinstance(web, dict) else []
    if not isinstance(results, list):
        raise ServiceError("A Brave Search devolveu resultados num formato inesperado.")
    lines = ["Notícias encontradas pela Brave Search" if news else "Resultados da Brave Search"]
    links, seen = [], set()
    for item in results:
        if not isinstance(item, dict):
            continue
        try:
            url = public_link(item.get("url"))
        except ValueError:
            continue
        if url in seen:
            continue
        seen.add(url)
        label = clean_text(item.get("title"), 180) or urlsplit(url).hostname
        snippet = clean_text(item.get("description"), 320)
        publisher = urlsplit(url).hostname
        stamp = clean_text(item.get("page_age"), 40) if news else ""
        if news:
            publisher += f" · data indicada {stamp}" if stamp else " · data indisponível"
        lines.append(f"{len(links)+1}. {label} · {publisher}" + (f"\n{snippet}" if snippet else ""))
        links.append({"label": label, "url": url})
        if len(links) == 8:
            break
    if not links:
        lines.append("Sem resultados para a pesquisa indicada.")
    return {"reply": "\n\n".join(lines), "links": links, "transient": True, "provider": "Brave Search"}


def location_label(place):
    return ", ".join(dict.fromkeys(clean_text(place.get(field), 80) for field in ("name", "admin1", "country")
                                   if isinstance(place.get(field), str) and place[field]))


def find_location(name, identifier):
    if identifier:
        places = [remote_json(GEO + "get", {"id": identifier}, "Open-Meteo")]
    else:
        data = remote_json(GEO + "search", {"name": name.strip(), "count": 6, "language": "pt"}, "Open-Meteo")
        places = data.get("results", [])
    valid = []
    if isinstance(places, list):
        for place in places:
            if not isinstance(place, dict):
                continue
            coords = [place.get(field) for field in ("latitude", "longitude")]
            if (type(place.get("id")) is int and isinstance(place.get("name"), str) and location_label(place)
                    and all(type(value) in {int, float} and isfinite(value) for value in coords)
                    and -90 <= coords[0] <= 90 and -180 <= coords[1] <= 180):
                valid.append(place)
    if not valid:
        raise ValueError("Não encontrei esse local. Indica o município ou o país.")
    if not identifier and len(valid) > 1:
        exact = [place for place in valid if normalize(place["name"]) == normalize(name.split(",", 1)[0].strip())]
        if exact:
            valid = exact
    return valid


def weather(name, identifier, when, hour):
    when = (when or ("hoje" if hour else "agora")).casefold()
    if hour:
        try:
            clock = time.fromisoformat(hour)
        except ValueError as error:
            raise ValueError("Indica uma hora válida no formato HH:MM.") from error
        if clock.minute or when == "agora":
            raise ValueError("A previsão horária usa horas certas. Indica um dia, por exemplo «amanhã às 15:00».")
    if when not in {"agora", "hoje", "amanhã"}:
        try:
            date.fromisoformat(when)
        except ValueError as error:
            raise ValueError("Indica a data da previsão no formato AAAA-MM-DD.") from error
    places = find_location(name, identifier)
    location_links = [{"label": "Geocodificação Open-Meteo", "url": "https://open-meteo.com/en/docs/geocoding-api"}]
    if len(places) > 1:
        suffix = f" {when}" + (f" às {hour}" if hour else "")
        options = [f"{location_label(place)} · «Meteorologia para local {place['id']}{suffix}»" for place in places]
        return {"reply": "Encontrei vários locais. Escolhe uma destas opções.\n" + "\n".join(options),
                "links": location_links, "provider": "Open-Meteo"}
    place = places[0]
    params = {
        "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
        "forecast_days": 16, "current": CURRENT_FIELDS, "daily": DAILY_FIELDS,
    }
    if hour:
        params["hourly"] = HOURLY_FIELDS
    data = remote_json(FORECAST, params, "Open-Meteo")
    try:
        current = data["current"]
        today = datetime.fromisoformat(current["time"]).date()
        zone = data["timezone"]
        if when == "agora":
            detail = weather_values(current, daily=False)
            moment = current["time"].replace("T", " ")
        else:
            day = today + timedelta(days=when == "amanhã") if when in {"hoje", "amanhã"} else date.fromisoformat(when)
            if not 0 <= (day - today).days <= 15:
                raise ValueError("Escolhe um dia entre hoje e os próximos 15 dias no local indicado.")
            table = data["hourly"] if hour else data["daily"]
            target = f"{day}T{hour}" if hour else day.isoformat()
            if target not in table["time"]:
                raise ValueError("A previsão não contém essa data ou hora local.")
            index = table["time"].index(target)
            detail = weather_values({key: values[index] for key, values in table.items()}, daily=not hour)
            moment = target.replace("T", " ")
    except (KeyError, TypeError, IndexError, AttributeError) as error:
        raise ServiceError("A previsão do Open-Meteo chegou incompleta.") from error
    links = [{"label": "Dados da previsão Open-Meteo", "url": FORECAST + "?" + urlencode(params)}, *location_links]
    return {"reply": f"{location_label(place)} · {moment} · {zone}\n{detail}",
            "links": links, "provider": "Open-Meteo"}


def measure(values, key, unit, label):
    value = values.get(key)
    if type(value) in {int, float} and isfinite(value):
        return f"{label} {value:g}{unit}"
    return ""


def weather_values(values, daily):
    code = values.get("weather_code")
    condition = CODES.get(code, "") if type(code) is int else ""
    fields = (
        ("temperature_2m_min", " °C", "mínima"), ("temperature_2m_max", " °C", "máxima"),
        ("precipitation_probability_max", "%", "probabilidade máx. de precipitação"),
        ("wind_speed_10m_max", " km/h", "vento máx."),
    ) if daily else (
        ("temperature_2m", " °C", "temperatura"), ("precipitation_probability", "%", "probabilidade de precipitação"),
        ("wind_speed_10m", " km/h", "vento"),
    )
    details = [condition, *(measure(values, *field) for field in fields)]
    return " · ".join(filter(None, details)) or "Dados de previsão indisponíveis para este intervalo."
