"""Comparar modelos locais em PT-PT com um conjunto fixo de pedidos."""
import argparse
import json
import re
from time import perf_counter
from urllib.request import Request, urlopen

from .check_local import check_ollama, request_json

BASE = "http://127.0.0.1:11434"
SYSTEM = {"role": "system", "content": "Responde brevemente em português de Portugal."}
TOOLS = [
    {"type": "function", "function": {
        "name": "listar_ficheiros",
        "description": "Lista os ficheiros na pasta autorizada. Usa . para a raiz.",
        "parameters": {"type": "object", "properties": {"pasta": {"type": "string"}},
                       "required": ["pasta"]},
    }},
    {"type": "function", "function": {
        "name": "consultar_agenda",
        "description": "Consulta os compromissos para uma data no formato AAAA-MM-DD.",
        "parameters": {"type": "object", "properties": {"data": {"type": "string"}},
                       "required": ["data"]},
    }},
]
CASES = [
    ("hora", "São 14h00. Que horas serão daqui a 45 minutos?", None, None),
    ("data", "Hoje é 14 de novembro de 2026. A que data corresponde amanhã?", None, None),
    ("ficheiros", "Que ficheiros tenho na pasta autorizada?", "listar_ficheiros", {"pasta": "."}),
    ("agenda", "Hoje é 14 de novembro de 2026. Que reuniões tenho amanhã?",
     "consultar_agenda", {"data": "2026-11-15"}),
]


def run_case(model, case):
    label, prompt, tool, arguments = case
    body = {
        "model": model, "messages": [SYSTEM, {"role": "user", "content": prompt}],
        "stream": True, "think": False,
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 128},
    }
    if tool:
        body["tools"] = TOOLS
    request = Request(BASE + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    start = perf_counter()
    first = None
    chunks = []
    calls = []
    with urlopen(request, timeout=180) as response:
        for line in response:
            event = json.loads(line)
            if "error" in event:
                raise RuntimeError(event["error"])
            message = event.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            if first is None and (content or tool_calls):
                first = perf_counter() - start
            chunks.append(content)
            calls.extend(tool_calls)
            if event.get("done"):
                break
        else:
            raise RuntimeError("Fluxo Ollama incompleto.")
    total = perf_counter() - start
    answer = "".join(chunks).strip()
    functions = [call["function"] for call in calls]
    if tool:
        success = len(functions) == 1 and functions[0]["name"] == tool and functions[0]["arguments"] == arguments
    elif label == "hora":
        success = bool(re.search(r"14\s*[:h]\s*45", answer))
    else:
        success = bool(re.search(r"15 de novembro de 2026|2026-11-15|15/11/2026", answer, re.I))
    return {"caso": label, "sucesso": success, "primeiro_s": round(first, 2) if first is not None else None,
            "total_s": round(total, 2), "resposta": answer, "chamadas": functions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="+")
    args = parser.parse_args()
    for model in args.models:
        check_ollama(model)
        outcomes = [run_case(model, case) for case in CASES]
        active = request_json(BASE + "/api/ps")["models"]
        running = next((entry for entry in active if entry["name"] == model), None)
        print(json.dumps({"modelo": model, "memoria_bytes": running["size"] if running else None,
                          "chamadas_corretas": sum(case["sucesso"] for case in outcomes[2:]),
                          "casos": outcomes}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
