"""Aplicar rascunhos revistos a integrações HTTPS com confirmação por recurso."""
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from uuid import uuid4

from jarvis.integrations.http_client import NoRedirect, public_link
from jarvis.personal.previews import preview_row, render_preview

PREPARE = re.compile(r'prepara ação "([a-zA-Z0-9_-]{1,40})" da pré-visualização (\d{1,18})(?: opção (\d))?[.!]?', re.I)
CONFIRM = re.compile(r'confirma (?:a )?ação externa (\d{1,18}) com ([a-f0-9]{8})[.!]?', re.I)
CANCEL = re.compile(r'cancela (?:a )?ação externa (\d{1,18})[.!]?', re.I)
STATUS = re.compile(r'(?:mostra|verifica) (?:a )?ação externa (\d{1,18})[.!]?', re.I)
LIST = re.compile(r'mostra (?:as )?ações externas disponíveis[.!]?', re.I)
KINDS = {"carrinho", "reserva", "formulário"}


def actions(memory):
    filename = os.environ.get("JARVIS_EXTERNAL_ACTIONS_FILE")
    if not filename:
        return {}
    try:
        with Path(filename).expanduser().open("rb") as stream:
            content = stream.read(64_001)
        if len(content) > 64_000:
            raise ValueError
        configured = json.loads(content.decode("utf-8-sig"))["perfis"].get(memory.path.stem, [])
        if not isinstance(configured, list) or len(configured) > 16:
            raise ValueError
        found = {}
        for action in configured:
            name = action["id"].casefold()
            kind = action["tipo"]
            url = action["url"]
            fields = action["campos"]
            secret = action.get("token_env")
            state_field, state = action["campo_estado"], action["estado_confirmado"]
            parsed = urlsplit(public_link(url.replace("{id}", "jarvis-resource")))
            if (not re.fullmatch(r"[a-z0-9_-]{1,40}", name) or name in found or kind not in KINDS
                    or parsed.scheme != "https" or parsed.query or parsed.fragment or url.count("{id}") != 1
                    or "{id}" not in urlsplit(url).path or any(char in url.replace("{id}", "") for char in "{}")
                    or action.get("contrato") != "put-idempotente"
                    or not re.fullmatch(r"[a-zA-Z0-9_-]{1,50}", state_field) or state_field in fields
                    or not isinstance(state, str) or not 1 <= len(state) <= 80
                    or (secret is not None and not re.fullmatch(r"JARVIS_ACTION_TOKEN_[A-Z0-9_]{1,40}", secret))
                    or not isinstance(fields, dict) or not 1 <= len(fields) <= 20
                    or not all(re.fullmatch(r"[a-zA-Z0-9_-]{1,50}", field)
                               and isinstance(selector, str) and 0 < len(selector) <= 160 for field, selector in fields.items())):
                raise ValueError
            if kind == "carrinho" and not {"total_centimos", "moeda"}.issubset(fields.values()):
                raise ValueError
            found[name] = {"name": name, "kind": kind, "url": url, "fields": fields, "secret": secret,
                           "state_field": state_field, "confirmed_state": state}
        return found
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        raise ValueError("Revê a configuração de ações externas para este perfil.") from error


def find_action(memory, name):
    item = actions(memory).get(name.casefold())
    if not item:
        raise ValueError("Essa ação externa não está autorizada neste perfil.")
    secret = os.environ.get(item["secret"], "") if item["secret"] else ""
    if item["secret"] and (not 1 <= len(secret) <= 8192 or any(not 33 <= ord(char) <= 126 for char in secret)):
        raise ValueError("Configura o token desta integração antes de executar uma ação externa.")
    fingerprint = hashlib.sha256(json.dumps([item, secret], sort_keys=True).encode()).hexdigest()
    return item, secret, fingerprint


def bind_payload(preview, action, selected):
    data = json.loads(preview["data"])
    values = {"rótulo": preview["label"], **data}
    if preview["kind"] == "carrinho":
        if data["shipping"] is None:
            raise ValueError("Indica os portes e confirma o total do carrinho antes de preparar a compra.")
        values["total_centimos"] = data["shipping"] + sum(row["quantity"] * row["unit"] for row in data["items"])
        values["moeda"] = data["currency"]
    if preview["kind"] == "reserva":
        options = data["choices"]
        if selected is None and len(options) == 1:
            selected = 1
        if selected is None or not 1 <= selected <= len(options):
            raise ValueError("Indica o número da opção de reserva que queres preparar.")
        values.pop("choices")
        values["opção"] = options[selected - 1]
        values["moeda"] = data["currency"]
    if preview["kind"] == "formulário":
        values["campos"] = dict(data["fields"])
    mapped = {}
    for name, selector in action["fields"].items():
        material = values
        for field in selector.split("."):
            if not isinstance(material, dict) or field not in material:
                raise ValueError(f"O campo {selector} não existe nos dados disponíveis para esta ação.")
            material = material[field]
        if material is None:
            raise ValueError(f"Preenche o campo {selector} antes de preparar a ação.")
        mapped[name] = material
    return mapped


def action_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    if LIST.fullmatch(command):
        available = actions(memory)
        return "\n".join(f"{name} · {entry['kind']}" for name, entry in available.items()) or "Sem ações externas configuradas."
    if match := PREPARE.fullmatch(command):
        return prepare(memory, match[1], int(match[2]), int(match[3]) if match[3] else None)
    if match := CONFIRM.fullmatch(command):
        return perform(memory, int(match[1]), match[2].casefold(), True)
    if match := STATUS.fullmatch(command):
        return perform(memory, int(match[1]), None, False)
    if match := CANCEL.fullmatch(command):
        changed = memory.execute(
            """UPDATE external_action_reviews SET state='cancelada'
               WHERE id=? AND state='a rever' RETURNING id""", (int(match[1]),),
        )
        return "Ação externa cancelada." if changed else "Essa ação não está a aguardar confirmação."
    return None


def prepare(memory, name, preview_id, selected):
    action, _, fingerprint = find_action(memory, name)
    preview = preview_row(memory, preview_id)
    if preview["kind"] != action["kind"]:
        raise ValueError("A pré-visualização e a integração têm tipos diferentes.")
    payload = bind_payload(preview, action, selected)
    reference = uuid4().hex
    row = memory.execute(
        """INSERT INTO external_action_reviews (preview_id, action, fingerprint, snapshot, payload, reference)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(preview_id, action, payload) DO UPDATE SET
             fingerprint=excluded.fingerprint, snapshot=excluded.snapshot, reference=excluded.reference, state='a rever'
           WHERE external_action_reviews.state IN ('cancelada','a rever') RETURNING id, reference""",
        (preview_id, action["name"], fingerprint, preview["data"], json.dumps(payload, ensure_ascii=False, sort_keys=True), reference),
    )
    if not row:
        raise ValueError("Já existe uma execução para estes dados. Consulta o estado da ação anterior.")
    row = row[0]
    reference = row["reference"]
    target = action["url"].replace("{id}", reference)
    return (f"Ação externa {row['id']} · {preview['label']}\nDestino — {target}\n\n{render_preview(preview)}\n\n"
            f"Campos que serão enviados\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
            f"Para executar, pede «Confirma a ação externa {row['id']} com {reference[:8]}».\n"
            f"Para recusar, pede «Cancela a ação externa {row['id']}».")


def request_result(url, secret, reference, payload=None):
    headers = {"Accept": "application/json"}
    if secret:
        headers["Authorization"] = "Bearer " + secret
    body = None
    if payload is not None:
        headers.update({"Content-Type": "application/json", "Idempotency-Key": reference})
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        request = Request(url, data=body, headers=headers, method="PUT" if body is not None else "GET")
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            content = response.read(140_001)
        if payload is not None:
            return "recebida", None
        if len(content) > 140_000:
            return "incerta", None
        result = json.loads(content)
        return ("encontrada", result) if isinstance(result, dict) else ("incerta", None)
    except HTTPError as error:
        error.close()
        if payload is None and error.code == 404:
            return "ausente", None
        return "incerta", None
    except (OSError, URLError, ValueError):
        return "incerta", None


def matching_result(data, payload):
    # Compare the expected values without coercing bools, numbers or strings.
    return all(key in data and json.dumps(data[key], sort_keys=True) == json.dumps(value, sort_keys=True)
               for key, value in payload.items())


def perform(memory, identifier, code, execute):
    rows = memory.execute("SELECT * FROM external_action_reviews WHERE id=?", (identifier,))
    if not rows:
        raise ValueError("Não encontrei essa ação no perfil atual.")
    row = rows[0]
    action, secret, fingerprint = find_action(memory, row["action"])
    if fingerprint != row["fingerprint"]:
        raise ValueError("A configuração mudou. Revê a integração antes de executar ou consultar.")
    if execute:
        preview = preview_row(memory, row["preview_id"])
        if preview["data"] != row["snapshot"]:
            raise ValueError("Os dados mudaram. Prepara uma nova revisão.")
        if code != row["reference"][:8]:
            raise ValueError("O código não corresponde à revisão.")
    if row["state"] in {"confirmada", "cancelada"}:
        return f"Ação externa {identifier} · {row['state']} · referência {row['reference']}."
    if not execute and row["state"] == "a rever":
        return f"Ação externa {identifier} · a aguardar confirmação."
    payload = json.loads(row["payload"])
    url = action["url"].replace("{id}", row["reference"])
    current, data = request_result(url, secret, row["reference"])
    if execute and current == "ausente":
        claimed = memory.execute(
            """UPDATE external_action_reviews SET state='por confirmar'
               WHERE id=? AND state IN ('a rever','por confirmar') AND fingerprint=? AND reference=?
                 AND EXISTS (SELECT 1 FROM local_previews WHERE id=? AND state<>'descartada' AND data=?)
               RETURNING id""", (identifier, fingerprint, row["reference"], row["preview_id"], row["snapshot"]),
        )
        if not claimed:
            return f"A ação {identifier} mudou durante a confirmação. Consulta o seu estado."
        request_result(url, secret, row["reference"], payload=payload)
        current, data = request_result(url, secret, row["reference"])
    if current == "encontrada" and data.get(action["state_field"]) == action["confirmed_state"] and matching_result(data, payload):
        completed = memory.execute(
            """UPDATE external_action_reviews SET state='confirmada'
               WHERE id=? AND reference=? AND state='por confirmar' RETURNING id""", (identifier, row["reference"]),
        )
        if completed:
            return f"Ação externa {identifier} confirmada no destino · referência {row['reference']}."
    if current == "encontrada":
        return "O destino tem um recurso para esta referência, mas a aplicação precisa de confirmar o estado e os campos."
    return f"Ação externa {identifier} por confirmar no destino · referência {row['reference']}."
