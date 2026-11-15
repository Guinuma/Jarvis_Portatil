"""Guardar observações e preparar relatórios de investigação com referências."""
import html
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

from jarvis.integrations.project_files import safe_path
from jarvis.integrations.http_client import public_link

IDENTIFIER = r"(\d{1,18})"
SAVE = re.compile(r'guarda pesquisa "([^"\r\n]{1,300})" com (.+)', re.I | re.S)
SHOW = re.compile(rf'(?:mostra|consulta) a pesquisa {IDENTIFIER}[.!]?', re.I)
LIST = re.compile(r'(?:mostra|consulta) as pesquisas guardadas[.!]?', re.I)
REPORT = re.compile(rf'(?:prepara|gera) (?:o )?relatório da pesquisa {IDENTIFIER}(?: para "([^"\r\n]{{1,500}})")?[.!]?', re.I)
SOURCE = re.compile(rf'(?:abre|mostra) a fonte (\d{{1,2}}) da pesquisa {IDENTIFIER}[.!]?', re.I)
TYPES = {"facto atribuído": "Facto atribuído", "inferência": "Inferência",
         "concordância": "Concordância", "divergência": "Divergência"}


def journal_command(text, memory, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := SAVE.fullmatch(command):
        entry = validate_entry(match[1], json.loads(match[2]))
        row = memory.execute(
            "INSERT INTO research_journal (question, details) VALUES (?, ?) RETURNING id",
            (entry["question"], json.dumps(entry, ensure_ascii=False)),
        )[0]
        return result(f"Pesquisa {row['id']} guardada neste perfil.", entry["sources"])
    if LIST.fullmatch(command):
        rows = memory.execute("SELECT id, question FROM research_journal ORDER BY id DESC LIMIT 20")
        return result("\n".join(f"{row['id']} · {row['question']}" for row in rows) or "Ainda não há pesquisas guardadas.")
    if match := SOURCE.fullmatch(command):
        number, identifier = map(int, match.groups())
        entry = get_entry(memory, identifier)
        if not 1 <= number <= len(entry["sources"]):
            raise ValueError("Indica um número de fonte existente nessa pesquisa.")
        selected = entry["sources"][number - 1]
        link = {"label": f"[{number}] {selected['title']}", "url": selected["url"]}
        return {"reply": selected["title"], "links": [link]}
    if match := REPORT.fullmatch(command):
        identifier = int(match[1])
        entry = get_entry(memory, identifier)
        if match[2]:
            target = safe_path(root, match[2])
            save_report(target, render_report(entry, markdown=True))
            return result(f"Relatório guardado em {target.relative_to(root)}.", entry["sources"])
        return result(render_report(entry), entry["sources"])
    if match := SHOW.fullmatch(command):
        identifier = int(match[1])
        entry = get_entry(memory, identifier)
        return result(render_report(entry), entry["sources"])
    return None


def get_entry(memory, identifier):
    rows = memory.execute("SELECT details FROM research_journal WHERE id=?", (identifier,))
    if not rows:
        raise ValueError("Não encontrei essa pesquisa neste perfil.")
    return json.loads(rows[0]["details"])


def field(value, limit):
    if not isinstance(value, str):
        raise ValueError("Indica valores de texto na pesquisa.")
    text = " ".join(value.split())
    if not 0 < len(text) <= limit:
        raise ValueError(f"Indica um texto de 1 a {limit} caracteres.")
    return text


def validate_entry(question, raw):
    if not isinstance(raw, dict) or "fontes" not in raw or set(raw) - {"fontes", "conclusões"}:
        raise ValueError("Indica uma lista de fontes e, opcionalmente, de conclusões.")
    sources, claims = raw["fontes"], raw.get("conclusões", [])
    if not isinstance(sources, list) or not 1 <= len(sources) <= 10:
        raise ValueError("Indica de uma a dez fontes na pesquisa.")
    if not isinstance(claims, list) or len(claims) > 12:
        raise ValueError("Indica até doze conclusões.")
    saved = []
    for source in sources:
        if not isinstance(source, dict) or not {"título", "url"} <= set(source) <= {"título", "url", "nota"}:
            raise ValueError("Cada fonte precisa de título e URL e pode ter uma nota.")
        saved.append({"title": field(source["título"], 160), "url": public_link(source["url"]),
                      "note": field(source["nota"], 500) if "nota" in source else ""})
    conclusions = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"tipo", "texto", "fontes"}:
            raise ValueError("Cada conclusão precisa de tipo, texto e números das fontes.")
        kind = field(claim["tipo"], 30).casefold()
        numbers = claim["fontes"]
        if kind not in TYPES or not isinstance(numbers, list) or not numbers or not all(
            type(number) is int and 1 <= number <= len(saved) for number in numbers
        ):
            raise ValueError("Escolhe facto atribuído, inferência, concordância ou divergência e indica as fontes válidas.")
        numbers = list(dict.fromkeys(numbers))
        if kind in {"concordância", "divergência"} and len({saved[number - 1]["url"] for number in numbers}) < 2:
            raise ValueError("Uma comparação precisa de pelo menos duas fontes distintas.")
        conclusions.append({"kind": kind, "text": field(claim["texto"], 600), "sources": numbers})
    return {"question": field(question, 300), "sources": saved, "claims": conclusions}


def result(reply, sources=()):
    return {"reply": reply, "links": [{"label": f"[{index}] {source['title']}", "url": source["url"]}
                                      for index, source in enumerate(sources, 1)]}


def markdown_text(text):
    return re.sub(r"([\\\[\]*_])", r"\\\1", html.escape(text, quote=False))


def markdown_url(url):
    return quote(url, safe=":/?#[]@!$&'*+,;=%~-._")


def render_report(entry, *, markdown=False):
    render = markdown_text if markdown else str
    heading = "## " if markdown else ""
    lines = [("# " if markdown else "") + render(entry["question"]), "", heading + "Conclusões"]
    if not entry["claims"]:
        lines.append("Ainda não foram registadas conclusões.")
    for claim in entry["claims"]:
        references = []
        for number in claim["sources"]:
            source = entry["sources"][number - 1]
            references.append(f"[{number}]({markdown_url(source['url'])})" if markdown else f"[{number}]")
        lines.append(f"- {TYPES[claim['kind']]} · {render(claim['text'])} · {' '.join(references)}")
    lines.extend(["", heading + "Fontes"])
    for number, source in enumerate(entry["sources"], 1):
        label = render(source["title"])
        if markdown:
            label = f"[{label}]({markdown_url(source['url'])})"
        lines.append(f"- [{number}] {label}" + (f" · {render(source['note'])}" if source["note"] else ""))
    return "\n".join(lines)


def save_report(target, content):
    if target.suffix.lower() != ".md":
        raise ValueError("Escolhe um destino Markdown com extensão .md.")
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=target.parent,
                                     suffix=".md", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content + "\n")
            stream.close()
            os.link(temporary, target)
        except FileExistsError as error:
            raise ValueError("Já existe um relatório nesse caminho. Escolhe outro nome.") from error
        finally:
            stream.close()
            temporary.unlink(missing_ok=True)
