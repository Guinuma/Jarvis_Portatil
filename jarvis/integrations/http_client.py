"""Pedidos HTTP e validação de ligações partilhados pelas integrações."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ServiceError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def remote_json(url, params, service, token=None, *, bearer=None):
    headers = {"Accept": "application/json", "User-Agent": "JarvisPortatil/1.0"}
    if token:
        headers["X-Subscription-Token"] = token
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    try:
        destination = url + "?" + urlencode(params) if params else url
        request = Request(destination, headers=headers)
        with build_opener(NoRedirect()).open(request, timeout=6) as response:
            content = response.read(1_000_001)
        if len(content) > 1_000_000:
            raise ServiceError(f"A resposta de {service} excedeu o limite de leitura.")
        data = json.loads(content)
    except HTTPError as error:
        with error:
            if error.code in {401, 403} and (token or bearer):
                raise ServiceError(f"A autenticação em {service} foi recusada. Revê a chave configurada.") from error
            if error.code == 429:
                raise ServiceError(f"{service} atingiu o limite de pedidos.") from error
            raise ServiceError(f"{service} devolveu um erro HTTP {error.code}.") from error
    except (URLError, TimeoutError, OSError, ValueError) as error:
        raise ServiceError(f"Não consegui obter uma resposta válida de {service}.") from error
    if not isinstance(data, dict) or data.get("error"):
        raise ServiceError(f"{service} devolveu uma resposta inesperada.")
    return data


def public_link(value):
    if not isinstance(value, str) or not 0 < len(value) <= 2000 or any(
        char.isspace() or ord(char) < 32 or char in '\\<>"' for char in value
    ):
        raise ValueError("Indica uma ligação HTTP ou HTTPS válida.")
    target = urlsplit(value)
    if target.scheme not in {"https", "http"} or not target.hostname or target.username or target.password:
        raise ValueError("Indica uma ligação HTTP ou HTTPS válida.")
    return value
