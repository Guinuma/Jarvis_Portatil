"""Ler fontes selecionadas e comparar as afirmações com excertos verificáveis."""
import json
import re
from concurrent.futures import ThreadPoolExecutor

from jarvis.integrations.editor import normalize
from jarvis.research.public_sources import origin_url, read_page
from jarvis.education.reasoning import LocalModelError, ask_local, object_schema, records_schema

READ = re.compile(r'(?:lê|consulta) (?:a )?fonte "([^"\r\n]{1,2000})"(?: sobre "([^"\r\n]{1,160})")?[.!]?', re.I)
PRICE = re.compile(r'consulta (?:o )?preço em "([^"\r\n]{1,2000})"[.!]?', re.I)
COMPARE = re.compile(r'compara fontes sobre "([^"\r\n]{1,300})" com (.+)', re.I | re.S)
TYPES = {"facto atribuído": "Afirmação atribuída à fonte", "inferência": "Inferência do modelo",
         "concordância": "Concordância", "divergência": "Divergência"}
STOPWORDS = set("sobre como para numa qual quais pelo pela onde entre com quando sao uma dos das que nos nas por".split())


def source_command(text):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := READ.fullmatch(command):
        page = read_page(match[1])
        excerpts = selected_blocks(page, match[2] or "", maximum=2000)
        lines = [page["title"], f"Consultada em {display_time(page)}."]
        if excerpts:
            lines.extend(f"- {block}" for block in excerpts[:5])
        else:
            lines.append("A origem respondeu, mas não encontrei texto legível.")
        return response("\n".join(lines), [page])
    if match := PRICE.fullmatch(command):
        page = read_page(match[1])
        lines = [page["title"], f"Preços anunciados na origem consultada em {display_time(page)}."]
        if page["prices"]:
            lines.extend(f"- {offer['label']} · {offer['amount'].replace('.', ',')} {offer['currency']}"
                         for offer in page["prices"])
        else:
            lines.append("A origem não indica um preço estruturado com moeda.")
        return response("\n".join(lines), [page])
    if match := COMPARE.fullmatch(command):
        return compare_pages(match[1], json.loads(match[2]))
    return None


def display_time(page):
    return page["read_at"].replace("T", " ").removesuffix("+00:00") + " UTC"


def response(text, pages):
    links = [{"label": f"[{index}] {page['title']}", "url": page["url"]} for index, page in enumerate(pages, 1)]
    return {"reply": text, "links": links, "transient": True, "provider": "Páginas de origem"}


def selected_blocks(page, query, maximum):
    terms = set(re.findall(r"[a-z0-9]{3,}", normalize(query))) - STOPWORDS
    atoms = []
    for line in page["blocks"]:
        # Keep cited text in contiguous chunks, with overlap for terms near a boundary.
        for start in range(0, len(line), 560):
            if candidate := line[max(0, start - 70):start + 630].strip():
                atoms.append(candidate)
    if terms:
        normalized = [set(re.findall(r"[a-z0-9]{3,}", normalize(block))) for block in atoms]
        matches = [(block, len(words & terms)) for block, words in zip(atoms, normalized)]
        atoms = [block for block, _ in sorted(matches, key=lambda entry: -entry[1])]
    blocks, length = [], 0
    for block in dict.fromkeys(atoms):
        if length + len(block) > maximum:
            remaining = maximum - length
            if remaining >= 160:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        length += len(block)
        if len(blocks) >= 16:
            break
    return blocks


def compare_pages(question, urls):
    if not isinstance(urls, list) or not 2 <= len(urls) <= 4:
        raise ValueError("Indica uma lista JSON com duas a quatro fontes HTTPS.")
    selected = [origin_url(url)[0] for url in urls]
    if len(set(selected)) != len(selected):
        raise ValueError("Escolhe fontes diferentes para a comparação.")
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(read_page, selected))
    if len({page["url"] for page in fetched}) != len(fetched):
        raise ValueError("Duas ligações conduzem à mesma página. Escolhe fontes de origem distintas.")
    sources = {index: selected_blocks(page, question, maximum=3400) for index, page in enumerate(fetched, 1)}
    if any(not blocks for blocks in sources.values()):
        raise ValueError("Pelo menos uma das fontes não disponibilizou texto para comparar.")
    annotated = [
        {"fonte": index, "título": fetched[index - 1]["title"], "excertos": blocks}
        for index, blocks in sources.items()
    ]
    schema = records_schema("itens", {
        "tipo": {"type": "string", "enum": list(TYPES)}, "texto": {"type": "string"},
        "evidências": {"type": "array", "items": object_schema({"fonte": {"type": "integer"}, "excerto": {"type": "string"}})},
    })
    output = ask_local(
        "Compara as fontes em relação à questão. Distingue afirmações atribuídas de inferências do modelo. "
        "Usa concordância ou divergência apenas se duas fontes diferentes permitirem essa comparação. "
        "Devolve até oito itens. Para cada item, copia uma frase ou parte de frase literalmente de cada fonte usada, "
        "com o número da fonte. Se não houver evidência, devolve a lista vazia. Não alteres citações.",
        {"questão": question, "fontes": annotated}, limit=2200, schema=schema,
    )
    lines = ["Comparação orientativa das páginas de origem"]
    kept, omitted = review_claims(output, sources)
    if kept:
        lines.extend(kept)
    else:
        lines.append("Não foi possível sustentar conclusões com citações verificáveis nos excertos lidos.")
    if omitted:
        lines.append(f"Omiti {omitted} item(ns) sem referências válidas nos excertos consultados.")
    return response("\n\n".join(lines), fetched)


def review_claims(output, sources):
    claims = output.get("itens") if isinstance(output, dict) else None
    if not isinstance(claims, list) or len(claims) > 8:
        raise LocalModelError("O modelo local não devolveu uma comparação válida.")
    kept, omitted = [], 0
    for claim in claims:
        item = verified_claim(claim, sources)
        if item:
            kept.append(item)
        else:
            omitted += 1
    return kept, omitted


def verified_claim(claim, sources):
    if not isinstance(claim, dict):
        return None
    kind, statement, evidence = claim.get("tipo"), claim.get("texto"), claim.get("evidências")
    if (not isinstance(kind, str) or kind not in TYPES or not isinstance(statement, str)
            or not statement.strip() or not isinstance(evidence, list) or not 1 <= len(evidence) <= len(sources)):
        return None
    references = {}
    for entry in evidence:
        if not isinstance(entry, dict) or type(entry.get("fonte")) is not int or not isinstance(entry.get("excerto"), str):
            return None
        index = entry["fonte"]
        excerpt = " ".join(entry["excerto"].split())
        if index not in sources or not 12 <= len(excerpt) <= 300 or not any(excerpt in block for block in sources[index]):
            return None
        references[index] = excerpt
    if kind in {"concordância", "divergência"} and len(references) < 2:
        return None
    quotes = "\n".join(f"[{index}] «{excerpt}»" for index, excerpt in references.items())
    return f"{TYPES[kind]} · {' '.join(statement.split())[:500]}\n{quotes}"
