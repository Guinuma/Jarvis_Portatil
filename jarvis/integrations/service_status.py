"""Diagnóstico de conectividade a pedido, sem interagir com o modelo."""
import os
from concurrent.futures import ThreadPoolExecutor

from jarvis.integrations.http_client import ServiceError, remote_json
from jarvis.research.web import FORECAST


def check_service(name, url, params, expected, *, bearer=None):
    try:
        payload = remote_json(url, params, name, bearer=bearer)
        if not payload.get(expected):
            return {"name": name, "detail": "Resposta recebida sem os dados esperados."}
    except ServiceError as error:
        return {"name": name, "detail": str(error)}
    return {"name": name, "detail": "Ligação disponível."}


def service_status(ollama_url, hermes_url, hermes_key):
    with ThreadPoolExecutor(max_workers=3) as pool:
        ollama = pool.submit(check_service, "Ollama", ollama_url, {}, "version")
        weather = pool.submit(check_service, "Open-Meteo", FORECAST,
                              {"latitude": 38.72, "longitude": -9.14, "current": "temperature_2m", "forecast_days": 1},
                              "current")
        hermes = pool.submit(check_service, "Hermes Agent", hermes_url, {}, "data", bearer=hermes_key) if hermes_key else None
        hermes_status = hermes.result() if hermes else {
            "name": "Hermes Agent", "detail": "A chave da API local ainda não está configurada.",
        }
        brave_status = {
            "name": "Brave Search",
            "detail": ("Chave configurada. Usa uma pesquisa para verificar o acesso."
                       if os.environ.get("JARVIS_BRAVE_SEARCH_KEY", "").strip()
                       else "A chave da API ainda não está configurada."),
        }
        traffic_status = {
            "name": "TomTom Routing",
            "detail": ("Chave configurada. Usa uma consulta de trânsito para verificar o acesso."
                       if os.environ.get("JARVIS_TOMTOM_KEY", "").strip()
                       else "A chave da API ainda não está configurada."),
        }
        return [ollama.result(), hermes_status, weather.result(), brave_status, traffic_status]
