"""Preparar carrinhos, reservas e formulários locais para revisão."""
import json
import re
from datetime import date, datetime

from jarvis.integrations.http_client import public_link
from jarvis.local_registers import saved_day

CREATE = re.compile(r'prepara (?:um |uma )?(carrinho|reserva|formulário|viagem) "([^"\r\n]{1,160})" com (.+)', re.I | re.S)
READ = re.compile(r'(?:mostra|consulta) (?:a )?pré-visualização (\d{1,18})[.!]?', re.I)
TRANSITION = re.compile(r'(?:marca (?:a )?pré-visualização (\d{1,18}) como revista|descarta (?:a )?pré-visualização (\d{1,18}))[.!]?', re.I)
LIST = re.compile(r'mostra (?:as )?pré-visualizações[.!]?', re.I)


def preview_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if match := CREATE.fullmatch(command):
        kind, label = match[1].casefold(), field(match[2], 160)
        raw = json.loads(match[3])
        validate = {"carrinho": cart_content, "reserva": booking_content,
                    "formulário": form_content, "viagem": trip_content}[kind]
        payload = validate(raw)
        row = memory.execute(
            "INSERT INTO local_previews (kind, label, data) VALUES (?, ?, ?) RETURNING id, kind, label, state, data",
            (kind, label, json.dumps(payload, ensure_ascii=False)),
        )[0]
        return render_preview(row)
    if match := READ.fullmatch(command):
        item = preview_row(memory, int(match[1]))
        return render_preview(item)
    if match := TRANSITION.fullmatch(command):
        identifier = int(match[1] or match[2])
        state = "revista" if match[1] else "descartada"
        rows = memory.execute(
            """UPDATE local_previews SET state=?, data=CASE WHEN ?='descartada' THEN '{}' ELSE data END
               WHERE id=? AND state<>'descartada' AND state<>? RETURNING id""",
            (state, state, identifier, state),
        )
        if not rows:
            raise ValueError("A pré-visualização não existe ou já tem esse estado.")
        return f"Pré-visualização {identifier} · {state}."
    if LIST.fullmatch(command):
        rows = memory.execute(
            "SELECT id, kind, label, state FROM local_previews WHERE state<>'descartada' ORDER BY id DESC LIMIT 20"
        )
        return "\n".join(f"{row['id']} · {row['kind']} · {row['label']} · {row['state']}" for row in rows) or "Sem pré-visualizações guardadas."
    return None


def field(value, limit):
    if not isinstance(value, str):
        raise ValueError("Indica valores de texto nos campos.")
    value = " ".join(value.split())
    if not 0 < len(value) <= limit:
        raise ValueError(f"Indica um valor de 1 a {limit} caracteres.")
    return value


def currency_code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]{3}", value):
        raise ValueError("Indica a moeda com três letras, por exemplo EUR.")
    return value.upper()


def cents(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{1,9}(?:[,.]\d{1,2})?", value):
        raise ValueError('Indica os preços entre aspas e com até duas casas decimais, por exemplo "12,90".')
    whole, _, fractional = value.replace(",", ".").partition(".")
    return int(whole) * 100 + int(fractional.ljust(2, "0"))


def price(value, currency):
    whole, fraction = divmod(value, 100)
    return f"{whole},{fraction:02d} {currency}"


def cart_content(raw):
    if not isinstance(raw, dict) or "artigos" not in raw or set(raw) - {"moeda", "artigos", "portes"}:
        raise ValueError("Indica os artigos do carrinho, a moeda e os portes quando forem conhecidos.")
    currency = currency_code(raw.get("moeda", "EUR"))
    products = raw["artigos"]
    if not isinstance(products, list) or not 1 <= len(products) <= 20:
        raise ValueError("Indica de 1 a 20 artigos.")
    rows = []
    for item in products:
        if not isinstance(item, dict) or set(item) != {"nome", "quantidade", "preço"}:
            raise ValueError("Cada artigo precisa de nome, quantidade e preço unitário.")
        amount = item["quantidade"]
        if type(amount) is not int or not 1 <= amount <= 999:
            raise ValueError("A quantidade de cada artigo deve estar entre 1 e 999.")
        rows.append({"name": field(item["nome"], 120), "quantity": amount, "unit": cents(item["preço"])})
    shipping = cents(raw["portes"]) if "portes" in raw else None
    return {"currency": currency, "items": rows, "shipping": shipping}


def booking_content(raw):
    if not isinstance(raw, dict) or "opções" not in raw or set(raw) - {"moeda", "opções"}:
        raise ValueError("Indica as opções da reserva, com datas, condições e custos quando conhecidos.")
    currency = currency_code(raw.get("moeda", "EUR"))
    choices = raw["opções"]
    if not isinstance(choices, list) or not 1 <= len(choices) <= 8:
        raise ValueError("Indica de 1 a 8 opções.")
    options = []
    for item in choices:
        must = {"nome", "início", "fim", "condições"}
        if not isinstance(item, dict) or not must <= set(item) <= must | {"total"}:
            raise ValueError("Cada opção precisa de nome, início, fim e condições. O total é opcional.")
        try:
            start, end = [saved_day(item[key]) for key in ("início", "fim")]
        except TypeError as error:
            raise ValueError("Usa datas AAAA-MM-DD nas opções.") from error
        if date.fromisoformat(start) > date.fromisoformat(end):
            raise ValueError("A data de fim deve ser igual ou posterior à inicial.")
        options.append({"name": field(item["nome"], 140), "start": start, "end": end,
                        "terms": field(item["condições"], 450),
                        "total": cents(item["total"]) if "total" in item else None})
    return {"currency": currency, "choices": options}


def trip_content(raw):
    if not isinstance(raw, dict) or set(raw) != {"dias", "transportes"}:
        raise ValueError("Indica os dias da viagem, os locais e as opções de transporte.")
    days, vehicles = raw["dias"], raw["transportes"]
    if not isinstance(days, list) or not 1 <= len(days) <= 14 or not isinstance(vehicles, list) or len(vehicles) > 20:
        raise ValueError("Indica de 1 a 14 dias e até 20 opções de transporte.")
    itinerary = {}
    for day in days:
        if not isinstance(day, dict) or set(day) != {"data", "locais"}:
            raise ValueError("Cada dia precisa de uma data e uma lista de locais.")
        stamp = saved_day(field(day["data"], 10))
        spots = day["locais"]
        if stamp in itinerary or not isinstance(spots, list) or not 1 <= len(spots) <= 8:
            raise ValueError("Usa datas diferentes e indica de 1 a 8 locais por dia.")
        itinerary[stamp] = [field(spot, 120) for spot in spots]
    options = []
    for vehicle in vehicles:
        required = {"meio", "origem", "destino", "partida", "chegada"}
        if not isinstance(vehicle, dict) or not required <= set(vehicle) <= required | {"url"}:
            raise ValueError("Cada transporte precisa de meio, origem, destino, partida e chegada.")
        departure, arrival = [trip_time(vehicle[key]) for key in ("partida", "chegada")]
        if arrival <= departure:
            raise ValueError("A chegada deve ser posterior à partida.")
        if not min(itinerary) <= departure.date().isoformat() <= max(itinerary):
            raise ValueError("A partida da opção de transporte deve estar dentro das datas da viagem.")
        minutes = int((arrival - departure).total_seconds() // 60)
        option = {"departure": departure.isoformat(timespec="minutes"), "arrival": arrival.isoformat(timespec="minutes"),
                  "mode": field(vehicle["meio"], 60), "from": field(vehicle["origem"], 120),
                  "to": field(vehicle["destino"], 120), "minutes": minutes,
                  "url": public_link(vehicle["url"]) if "url" in vehicle else ""}
        options.append(option)
    return {"itinerary": dict(sorted(itinerary.items())), "transports": options}


def trip_time(value):
    text = field(value, 35)
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError("Usa data, hora e fuso, por exemplo 2026-12-01T09:00+00:00.") from error
    if stamp.utcoffset() is None or stamp.second or stamp.microsecond:
        raise ValueError("Indica a hora em minutos e inclui o fuso horário.")
    return stamp


def render_trip(content):
    lines = ["Locais por dia"]
    lines.extend(f"- {day} · {', '.join(places)}" for day, places in content["itinerary"].items())
    lines.append("\nOpções de transporte indicadas")
    for item in content["transports"]:
        hours, minutes = divmod(item["minutes"], 60)
        line = (f"- {item['mode']} · {item['from']} → {item['to']} · {item['departure']} a {item['arrival']}"
                f" · {hours} h {minutes:02} min")
        if item["url"]:
            line += "\n  " + item["url"]
        lines.append(line)
    if not content["transports"]:
        lines.append("Ainda não foram indicadas opções de transporte.")
    return lines


def form_content(raw):
    if not isinstance(raw, dict) or not 1 <= len(raw) <= 20:
        raise ValueError("Indica até 20 pares com o nome do campo e o valor a preencher.")
    return {"fields": [(field(name, 100), field(value, 450)) for name, value in raw.items()]}


def preview_row(memory, identifier):
    items = memory.execute(
        "SELECT id, kind, label, state, data FROM local_previews WHERE id=? AND state<>'descartada'", (identifier,),
    )
    if not items:
        raise ValueError("Não encontrei essa pré-visualização neste perfil.")
    return items[0]


def render_preview(record):
    identifier, state, kind = record["id"], record["state"], record["kind"]
    content = json.loads(record["data"])
    lines = [f"Pré-visualização {identifier} · {kind} · {state}", record["label"]]
    if kind == "carrinho":
        money = content["currency"]
        subtotal = 0
        for item in content["items"]:
            amount = item["quantity"] * item["unit"]
            subtotal += amount
            lines.append(f"- {item['name']} · {item['quantity']} × {price(item['unit'], money)} · {price(amount, money)}")
        shipping = content["shipping"]
        if shipping is None:
            lines.append(f"Subtotal {price(subtotal, money)} · portes por indicar")
        else:
            lines.append(f"Portes {price(shipping, money)} · total {price(subtotal + shipping, money)}")
    elif kind == "reserva":
        for choice in content["choices"]:
            cost = price(choice["total"], content["currency"]) if choice["total"] is not None else "total por indicar"
            lines.append(f"- {choice['name']} · {choice['start']} a {choice['end']} · {cost}\n  {choice['terms']}")
    elif kind == "viagem":
        lines.extend(render_trip(content))
    else:
        lines.extend(f"- {key} · {value}" for key, value in content["fields"])
    lines.append("\nRascunho local para revisão.")
    if state == "a rever":
        lines.append(f'Quando terminares, pede «Marca a pré-visualização {identifier} como revista».')
    return "\n".join(lines)
