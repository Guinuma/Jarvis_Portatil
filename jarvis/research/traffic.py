"""Consultar estimativas de trânsito para trajetos de carro."""
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from jarvis.integrations.http_client import ServiceError, remote_json
from jarvis.research.web import find_location, location_label

POINT = r'(?:"([^"\r\n]{2,120})"|local (\d{1,12}))'
TRAFFIC = re.compile(rf'(?:consulta (?:o )?)?trânsito de {POINT} para {POINT}[.!]?', re.I)
ROUTING = "https://api.tomtom.com/routing/1/calculateRoute/"
SOURCE = "https://docs.tomtom.com/routing-api/documentation/tomtom-maps/v1/calculate-route"
COORDINATES = re.compile(r"\s*([+-]?\d{1,3}(?:\.\d{1,8})?)\s*,\s*([+-]?\d{1,3}(?:\.\d{1,8})?)\s*")


def traffic_command(text):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    match = TRAFFIC.fullmatch(command)
    if not match:
        return None
    origin, origin_id, destination, destination_id = match.groups()
    key = os.environ.get("JARVIS_TOMTOM_KEY", "").strip()
    if not key:
        raise ValueError("Configura JARVIS_TOMTOM_KEY no ambiente do JARVIS para consultar o trânsito.")
    with ThreadPoolExecutor(max_workers=2) as pool:
        start = pool.submit(route_points, origin, origin_id)
        end = pool.submit(route_points, destination, destination_id)
        starts, destinations = start.result(), end.result()
    if len(starts) > 1:
        options = [f"{location_label(place)} · «Trânsito de local {place['id']} para {input_label(destination, destination_id)}»"
                   for place in starts]
        return result("Encontrei várias origens. Escolhe uma destas opções.\n" + "\n".join(options))
    if len(destinations) > 1:
        options = [f"{location_label(place)} · «Trânsito de {input_label(origin, origin_id)} para local {place['id']}»"
                   for place in destinations]
        return result("Encontrei vários destinos. Escolhe uma destas opções.\n" + "\n".join(options))
    return route_estimate(starts[0], destinations[0], key)


def route_points(name, identifier):
    if name and (match := COORDINATES.fullmatch(name)):
        latitude, longitude = map(float, match.groups())
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise ValueError("As coordenadas precisam de latitude entre -90 e 90 e longitude entre -180 e 180.")
        return [{"name": f"{latitude:.5f}, {longitude:.5f}", "latitude": latitude, "longitude": longitude}]
    return find_location(name, identifier)


def input_label(name, identifier):
    return f"local {identifier}" if identifier else f'"{name}"'


def seconds_text(seconds):
    minutes = (seconds + 30) // 60
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02} min" if hours else f"{minutes} min"


def route_estimate(origin, destination, key):
    coordinates = ":".join(f"{place['latitude']:.6f},{place['longitude']:.6f}" for place in (origin, destination))
    if coordinates.split(":")[0] == coordinates.split(":")[1]:
        raise ValueError("Escolhe pontos diferentes para a origem e o destino.")
    data = remote_json(ROUTING + coordinates + "/json", {
        "key": key, "traffic": "true", "routeType": "fastest", "travelMode": "car",
        "routeRepresentation": "summaryOnly",
    }, "TomTom Routing")
    routes = data.get("routes")
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
        raise ServiceError("A TomTom não encontrou um percurso de carro para estes pontos.")
    summary = routes[0].get("summary")
    if not isinstance(summary, dict):
        raise ServiceError("O serviço devolveu um percurso sem resumo.")
    distance, duration, delay = (summary.get(field) for field in
                                 ("lengthInMeters", "travelTimeInSeconds", "trafficDelayInSeconds"))
    if not all(type(value) is int and 0 <= value < 100_000_000 for value in (distance, duration)):
        raise ServiceError("O serviço devolveu uma estimativa de percurso inválida.")
    stamp = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M UTC")
    lines = [
        f"{location_label(origin)} → {location_label(destination)}",
        f"Distância {distance / 1000:.1f} km · duração estimada {seconds_text(duration)}",
    ]
    if type(delay) is int and 0 <= delay < 100_000_000:
        lines.append(f"Atraso estimado associado ao trânsito · {seconds_text(delay)}")
    lines.append(f"Estimativa da TomTom consultada em {stamp}.")
    return result("\n".join(lines))


def result(text):
    return {"reply": text, "links": [{"label": "Fonte · TomTom Routing API", "url": SOURCE}],
            "transient": True, "provider": "TomTom Routing"}
