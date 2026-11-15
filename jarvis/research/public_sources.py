"""Ler texto de origens HTTPS públicas, com limites de rede e de conteúdo."""
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from jarvis.integrations.http_client import ServiceError, public_link

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 4
ADDRESS_TRANSLATORS = tuple(ipaddress.ip_network(prefix) for prefix in ("64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32"))
TLS_CONTEXT = ssl.create_default_context()
TLS_CONTEXT.set_alpn_protocols(["http/1.1"])
OFFER_METADATA = {"product:price:amount", "product:price:currency", "og:price:amount", "og:price:currency"}


def origin_url(value):
    try:
        url = urlsplit(public_link(value))
        if url.scheme != "https" or url.port not in (None, 443):
            raise ValueError
        host = url.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        if not host or "%" in host or len(host) > 253:
            raise ValueError
        if ":" in host:
            netloc = f"[{ipaddress.IPv6Address(host)}]"
        else:
            if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host):
                raise ValueError
            netloc = host
        return urlunsplit(("https", netloc, url.path or "/", url.query, "")), host
    except (AttributeError, ValueError, UnicodeError) as error:
        raise ValueError("Indica um endereço público HTTPS na porta normal.") from error


def public_address(value):
    address = ipaddress.ip_address(value)
    return (address.is_global and not (address.is_multicast or address.is_reserved or address.is_loopback
                                      or address.is_link_local or address.is_unspecified)
            and (address.version == 4 or (not address.ipv4_mapped and not any(address in block for block in ADDRESS_TRANSLATORS))))


def verified_endpoints(host):
    try:
        resolved = socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    except OSError as error:
        raise ServiceError("Não consegui encontrar o servidor da fonte.") from error
    endpoints = []
    for family, _, _, _, address in resolved:
        if family not in (socket.AF_INET, socket.AF_INET6) or not public_address(address[0]):
            raise ValueError("A fonte resolve para um endereço que não é público.")
        endpoint = (family, address)
        if endpoint not in endpoints:
            endpoints.append(endpoint)
    if not endpoints:
        raise ServiceError("A fonte não apresentou um endereço público.")
    return endpoints[:3]


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, endpoint, timeout):
        super().__init__(host, 443, timeout=timeout, context=TLS_CONTEXT)
        self.endpoint = endpoint

    def connect(self):
        family, address = self.endpoint
        raw_socket = socket.socket(family, socket.SOCK_STREAM)
        try:
            raw_socket.settimeout(self.timeout)
            raw_socket.connect(address)
            self.sock = TLS_CONTEXT.wrap_socket(raw_socket, server_hostname=self.host)
        except BaseException:
            raw_socket.close()
            raise


def request_target(url):
    parsed = urlsplit(url)
    path = quote(parsed.path, safe="/%:@!$&'()*+,;=-._~")
    if parsed.query:
        path += "?" + quote(parsed.query, safe="/%?:@!$&'()*+,;=-._~")
    return path


def fetch_response(url, host, expiry):
    for endpoint in verified_endpoints(host):
        remaining = expiry - time.monotonic()
        if remaining <= 0:
            break
        connection = PinnedHTTPS(host, endpoint, min(remaining, 5))
        try:
            connection.request("GET", request_target(url), headers={
                "Accept": "text/html, application/xhtml+xml, text/plain",
                "Accept-Encoding": "identity", "User-Agent": "JARVIS-Portatil/1.0",
                "Connection": "close",
            })
            return connection, connection.getresponse()
        except (OSError, http.client.HTTPException):
            connection.close()
    raise ServiceError("Não consegui estabelecer uma ligação HTTPS válida à fonte.")


def body_bytes(response, expiry):
    chunks, size = [], 0
    expected = response.length
    if expected is not None and expected > MAX_BYTES:
        raise ServiceError("A página excede o limite de 1,5 MB.")
    while time.monotonic() < expiry:
        chunk = response.read1(min(32_768, MAX_BYTES + 1 - size))
        if not chunk:
            if expected is not None and size != expected:
                raise ServiceError("A página chegou incompleta.")
            return b"".join(chunks)
        size += len(chunk)
        if size > MAX_BYTES:
            raise ServiceError("A página excede o limite de 1,5 MB.")
        chunks.append(chunk)
    raise ServiceError("O servidor demorou demasiado a enviar a página.")


def decode_page(body, charset):
    if not charset:
        meta = re.search(rb"<meta\b[^>]*charset\s*=\s*['\"]?([A-Za-z0-9_.-]{1,40})", body[:8192], re.I)
        charset = meta[1].decode("ascii") if meta else "utf-8-sig"
    try:
        return body.decode(charset, errors="replace")
    except (LookupError, TypeError, ValueError):
        return body.decode("utf-8-sig", errors="replace")


def read_page(value):
    expiry = time.monotonic() + 14
    url, host = origin_url(value)
    seen = set()
    for _ in range(MAX_REDIRECTS + 1):
        if url in seen:
            raise ServiceError("A fonte entrou num ciclo de redirecionamentos.")
        seen.add(url)
        connection, response = fetch_response(url, host, expiry)
        try:
            with response:
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.getheader("Location")
                    if not location:
                        raise ServiceError("A origem redirecionou sem indicar o destino.")
                    url, host = origin_url(urljoin(url, location))
                    continue
                if response.status != 200:
                    raise ServiceError(f"A origem respondeu com HTTP {response.status}.")
                kind = response.headers.get_content_type()
                encoding = response.getheader("Content-Encoding", "identity").lower().strip()
                if kind not in {"text/html", "application/xhtml+xml", "text/plain"} or encoding != "identity":
                    raise ServiceError("A origem precisa de disponibilizar uma página HTML ou texto simples sem compressão.")
                try:
                    body = body_bytes(response, expiry)
                except (OSError, http.client.HTTPException) as error:
                    raise ServiceError("A ligação à origem terminou antes de receber a página.") from error
                return parse_page(url, host, decode_page(body, response.headers.get_content_charset()), kind)
        finally:
            connection.close()
    raise ServiceError("A origem excedeu o limite de redirecionamentos.")


class SourceHTML(HTMLParser):
    BLOCKS = {"p", "div", "li", "section", "blockquote", "tr", "br", "h1", "h2", "h3", "h4", "pre"}
    HIDDEN = {"script", "style", "nav", "footer", "header", "template", "svg", "noscript"}
    PRIMARY = {"article", "main"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = []
        self.in_title = False
        self.in_head = False
        self.hidden = []
        self.primary = []
        self.main = []
        self.all = []
        self.metadata = {}
        self.data_blocks = []
        self.active_data = None

    def append(self, text):
        self.all.append(text)
        if self.primary:
            self.main.append(text)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "head":
            self.in_head = True
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = (values.get("property") or "").casefold()
            content = values.get("content") or ""
            if key in OFFER_METADATA and key not in self.metadata:
                self.metadata[key] = content[:80]
        if tag == "script" and (values.get("type") or "").lower() == "application/ld+json":
            self.active_data = [] if len(self.data_blocks) < 10 else None
        if tag in self.HIDDEN:
            self.hidden.append(tag)
        if self.hidden or self.in_head:
            return
        if tag in self.PRIMARY:
            self.primary.append(tag)
        if tag in self.BLOCKS or tag in self.PRIMARY:
            self.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "head":
            self.in_head = False
        if self.hidden:
            if self.hidden[-1] == tag:
                self.hidden.pop()
            if tag == "script" and self.active_data is not None:
                self.data_blocks.append("".join(self.active_data))
                self.active_data = None
            return
        if tag in self.BLOCKS or tag in self.PRIMARY:
            self.append("\n")
        if self.primary and self.primary[-1] == tag:
            self.primary.pop()

    def handle_data(self, text):
        if self.active_data is not None:
            self.active_data.append(text[:150_000])
        elif self.in_title:
            self.title.append(text)
        elif not self.hidden and not self.in_head:
            self.append(text)


def paragraphs(text):
    output = []
    for line in text.splitlines():
        body = " ".join(line.split())
        if body:
            output.append(body)
    return output


def parse_page(url, host, text, kind):
    title, blocks, offers = host, paragraphs(text), []
    if kind != "text/plain":
        parser = SourceHTML()
        try:
            parser.feed(text)
            parser.close()
        except (ValueError, AssertionError) as error:
            raise ServiceError("Não consegui ler o HTML entregue pela origem.") from error
        title = " ".join("".join(parser.title).split())[:180] or host
        primary = paragraphs("".join(parser.main))
        blocks = primary if sum(map(len, primary)) > 200 else paragraphs("".join(parser.all))
        offers = extract_prices(parser.metadata, parser.data_blocks)
    return {"url": url, "title": title, "blocks": blocks, "prices": offers,
            "read_at": datetime.now(timezone.utc).isoformat(timespec="minutes")}


def parse_amount(raw, currency):
    if type(raw) not in {str, int, float} or not isinstance(currency, str):
        return None
    text = str(raw).strip()
    code = currency.strip().upper()
    if not re.fullmatch(r"\d{1,12}(?:[.,]\d{1,6})?", text) or not re.fullmatch(r"[A-Z]{3}", code):
        return None
    try:
        return format(Decimal(text.replace(",", ".")), "f"), code
    except InvalidOperation:
        return None


def extract_prices(metadata, structured):
    offers = []
    for prefix in ("product", "og"):
        if amount := parse_amount(metadata.get(f"{prefix}:price:amount"), metadata.get(f"{prefix}:price:currency")):
            offers.append({"label": "Preço anunciado", "amount": amount[0], "currency": amount[1]})

    for document in structured:
        try:
            tree = json.loads(document)
        except (ValueError, RecursionError):
            continue
        nodes = deque([tree])
        for _ in range(600):
            if not nodes or len(offers) >= 15:
                break
            node = nodes.popleft()
            if isinstance(node, list):
                nodes.extend(node[:100])
                continue
            if not isinstance(node, dict):
                continue
            kinds = node.get("@type")
            kinds = kinds if isinstance(kinds, list) else [kinds]
            kinds = {item.rsplit("/", 1)[-1].removeprefix("schema:") for item in kinds if isinstance(item, str)}
            if "Offer" in kinds:
                if amount := parse_amount(node.get("price"), node.get("priceCurrency")):
                    offers.append({"label": "Oferta anunciada", "amount": amount[0], "currency": amount[1]})
            if "AggregateOffer" in kinds:
                for field, label in (("lowPrice", "Preço mais baixo anunciado"), ("highPrice", "Preço mais alto anunciado")):
                    if amount := parse_amount(node.get(field), node.get("priceCurrency")):
                        offers.append({"label": label, "amount": amount[0], "currency": amount[1]})
            nodes.extend(value for value in node.values() if isinstance(value, (list, dict)))
    unique = {}
    for offer in offers:
        key = (Decimal(offer["amount"]).normalize(), offer["currency"])
        unique.setdefault(key, offer)
    return list(unique.values())[:6]
