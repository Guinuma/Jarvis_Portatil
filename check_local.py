"""Verificar a ligação local entre o JARVIS, o Ollama e o Hermes Agent."""
import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(url, payload=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    with urlopen(Request(url, data=body, headers=headers), timeout=120) as response:
        return json.load(response)


def check_ollama(model):
    base_url = "http://127.0.0.1:11434"
    version = request_json(f"{base_url}/api/version")["version"]
    capabilities = request_json(f"{base_url}/api/show", {"model": model})["capabilities"]
    if "tools" not in capabilities:
        raise ValueError(f"O modelo {model} não anuncia suporte a ferramentas.")
    print(f"Ollama {version}: {model} anuncia suporte a ferramentas.")


def check_hermes(key):
    response = request_json(
        "http://127.0.0.1:8642/v1/chat/completions",
        {
            "model": "hermes-agent",
            "messages": [{
                "role": "user",
                "content": (
                    "Responde em português de Portugal. "
                    "Se forem 14h00, que horas serão daqui a 45 minutos? "
                    "Responde sem usar ferramentas."
                ),
            }],
            "stream": False,
        },
        key,
    )
    answer = response["choices"][0]["message"]["content"].strip()
    if "14:45" not in answer and "14h45" not in answer:
        raise ValueError(f"O Hermes respondeu, mas não devolveu a hora esperada: {answer}")
    print(f"Resposta do Hermes: {answer}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.environ.get("JARVIS_MODEL", "qwen3:8b"))
    parser.add_argument("--ollama-only", action="store_true", help="Verifica apenas o Ollama.")
    args = parser.parse_args()

    try:
        check_ollama(args.model)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError) as error:
        print(f"Ollama: {error}. Confirma que está aberto e que {args.model} está instalado.", file=sys.stderr)
        return 1

    if args.ollama_only:
        return 0

    key = os.environ.get("JARVIS_HERMES_API_KEY")
    if not key:
        print("Define JARVIS_HERMES_API_KEY com a chave da API local do Hermes.", file=sys.stderr)
        return 1

    try:
        check_hermes(key)
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError, IndexError, AttributeError) as error:
        print(f"Hermes Agent: {error}. Confirma que a API local está ativa e que a chave está correta.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
