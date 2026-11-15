"""Executar fluxos de navegação e preenchimento autorizados pelo operador."""
import json
import os
import re
import subprocess
from pathlib import Path

from jarvis.personal.previews import preview_row

NAVIGATE = re.compile(r'executa navegação visual "([a-zA-Z0-9_-]{1,40})"[.!]?', re.I)
FILL = re.compile(r'preenche o formulário visual "([a-zA-Z0-9_-]{1,40})" da pré-visualização (\d{1,18})[.!]?', re.I)
FIELDS = re.compile(r"[\w. -]{1,120}")


def windows_ui_command(text, memory):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    navigation, form = NAVIGATE.fullmatch(command), FILL.fullmatch(command)
    if not navigation and not form:
        return None
    identifier = (navigation or form)[1].casefold()
    config = configuration(memory)
    entry = config.get(identifier)
    if not entry or entry["tipo"] != ("navegação" if navigation else "formulário"):
        raise ValueError("Esse fluxo visual não está configurado neste perfil.")
    request = {
        "type": entry["tipo"], "process": entry["processo"], "window": entry["janela"],
        "destination": entry.get("janela_final", entry["janela"]),
    }
    if navigation:
        request["steps"] = entry["passos"]
    else:
        record = preview_row(memory, int(form[2]))
        if record["kind"] != "formulário":
            raise ValueError("Indica uma pré-visualização de formulário.")
        fields = dict(json.loads(record["data"])["fields"])
        mapping = entry["campos"]
        if set(fields) != set(mapping):
            raise ValueError("Os campos guardados precisam de corresponder aos campos autorizados do formulário visual.")
        request["fields"] = [{"name": name, "id": mapping[name], "value": value} for name, value in fields.items()]
    script = Path(__file__).resolve().parents[2] / "scripts" / "uia_review.ps1"
    env = dict(os.environ, JARVIS_UIA_REQUEST=json.dumps(request, ensure_ascii=False))
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script)],
            env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=40,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise ValueError("Não consegui executar o fluxo visual no Windows.") from error
    if not isinstance(payload, dict):
        raise ValueError("O Windows não devolveu o resultado esperado.")
    if result.returncode or "erro" in payload:
        raise ValueError(payload.get("erro", "O fluxo visual falhou. Confere os campos já alterados."))
    lines = [f"Fluxo visual {identifier} · {payload['estado']}"]
    lines.extend(f"- {entry['name']} · {entry['value']}" for entry in payload.get("campos", []))
    return "\n".join(lines)


def configuration(memory):
    filename = os.environ.get("JARVIS_WINDOWS_ACTIONS_FILE")
    if not filename:
        return {}
    try:
        with Path(filename).expanduser().open("rb") as stream:
            raw = stream.read(64_001)
        if len(raw) > 64_000:
            raise ValueError
        profiles = json.loads(raw.decode("utf-8-sig"))["perfis"]
        configurations = profiles.get(memory.path.stem, {})
        if not isinstance(configurations, dict) or len(configurations) > 15:
            raise ValueError
        return {name: validate(flow) for name, flow in configurations.items()}
    except (OSError, AttributeError, TypeError, ValueError, KeyError) as error:
        raise ValueError("Revê a configuração dos fluxos visuais deste perfil.") from error


def validate(flow):
    if (not isinstance(flow, dict) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,80}", flow["processo"])
            or not all(isinstance(field, str) and 0 < len(field) <= 160
                       for field in (flow["janela"], flow.get("janela_final", flow["janela"])))):
        raise ValueError
    kind = flow["tipo"]
    if kind == "navegação":
        steps = flow["passos"]
        if not isinstance(steps, list) or not 1 <= len(steps) <= 5 or not all(
            isinstance(step, dict) and set(step) == {"invocar", "esperar"}
            and all(isinstance(value, str) and FIELDS.fullmatch(value) for value in step.values()) for step in steps
        ):
            raise ValueError
    elif kind == "formulário":
        fields = flow["campos"]
        if not isinstance(fields, dict) or not 1 <= len(fields) <= 12 or not all(
            isinstance(value, str) and FIELDS.fullmatch(value) for value in fields.values()
        ) or len(set(fields.values())) != len(fields):
            raise ValueError
    else:
        raise ValueError
    return flow
