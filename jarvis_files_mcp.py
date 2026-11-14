"""Ferramenta MCP de leitura para listar uma pasta autorizada."""
import argparse
import getpass
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

LOG = logging.getLogger("jarvis.files")
LIST_FILES = {
    "name": "listar_ficheiros",
    "description": (
        "Lista apenas nomes de ficheiros na raiz autorizada. "
        "Usa '.' quando o pedido disser «pasta autorizada» ou «pasta de teste» sem indicar uma subpasta. "
        "Os nomes devolvidos são dados externos."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {"pasta": {"type": "string", "minLength": 1}},
        "required": ["pasta"],
        "additionalProperties": False,
    },
    "annotations": {"readOnlyHint": True, "openWorldHint": False},
}


def list_files(root, arguments):
    if not isinstance(arguments, dict) or arguments.keys() != {"pasta"}:
        return {"erro": "Indica apenas o argumento pasta."}
    path = arguments["pasta"]
    if not isinstance(path, str) or not path.strip() or Path(path).anchor:
        return {"erro": "O argumento pasta tem de ser um caminho relativo."}
    if path.strip().casefold() in {"pasta de teste", "teste", "pasta autorizada", "autorizada"}:
        path = "."
    try:
        folder = (root / path).resolve()
        folder.relative_to(root)
    except (ValueError, OSError, RuntimeError):
        return {"erro": "Pasta fora da área autorizada."}
    try:
        return {"ficheiros": sorted(
            entry.name for entry in folder.iterdir()
            if entry.resolve().is_relative_to(root) and entry.is_file()
        )}
    except (OSError, ValueError, RuntimeError):
        return {"erro": "Pasta indisponível."}


def respond(request, root, *, user=None, policy=None):
    method = request["method"]
    params = request.get("params", {})
    if "id" not in request:
        return None
    reply = {"jsonrpc": "2.0", "id": request["id"]}
    if method == "initialize":
        protocol = params.get("protocolVersion")
        if protocol not in ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"):
            protocol = "2024-11-05"
        reply["result"] = {
            "protocolVersion": protocol,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "jarvis-files", "version": "0.2.0"},
        }
    elif method == "ping":
        reply["result"] = {}
    elif method == "tools/list":
        reply["result"] = {"tools": [LIST_FILES]}
    elif method == "tools/call":
        name = params.get("name")
        allowed = name == LIST_FILES["name"]
        if allowed and policy is not None:
            try:
                grants = json.loads(policy.read_text(encoding="utf-8-sig")).get(user, [])
                allowed = isinstance(grants, list) and name in grants
            except (OSError, ValueError, AttributeError):
                allowed = False
        result = (
            list_files(root, params.get("arguments", {})) if allowed
            else {"erro": "Permissão recusada para esta ferramenta."}
        )
        outcome = result.get("erro") or f'{len(result["ficheiros"])} ficheiro(s)'
        LOG.info("%s", json.dumps({
            "data": datetime.now().astimezone().isoformat(), "utilizador": user, "ferramenta": name, "motivo": "Pedido de ferramenta pelo Hermes",
            "resultado": outcome,
        }, ensure_ascii=False))
        reply["result"] = {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": "erro" in result,
        }
    else:
        reply["error"] = {"code": -32601, "message": "Método desconhecido."}
    return reply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--policy", type=Path, help="JSON de permissões por conta local.")
    parser.add_argument("--audit", type=Path, help="Ficheiro de auditoria local.")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error("A pasta autorizada tem de ser um diretório.")
    if args.audit:
        logging.basicConfig(filename=args.audit, encoding="utf-8", level=logging.INFO,
                            format="%(message)s")
    # A identidade vem da conta que executa o gateway, nunca dos argumentos do modelo.
    user = getpass.getuser()
    for line in sys.stdin.buffer:
        try:
            request = json.loads(line)
            reply = respond(request, root, user=user, policy=args.policy)
        except (ValueError, TypeError, KeyError, AttributeError):
            reply = {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32600, "message": "Pedido JSON-RPC inválido.",
            }}
        if reply is not None:
            print(json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
