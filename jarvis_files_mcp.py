"""Ferramenta MCP de leitura para listar uma pasta autorizada."""
import argparse
import json
import sys
from pathlib import Path



LIST_FILES = {
    "name": "listar_ficheiros",
    "description": (
        "Lista apenas nomes de ficheiros dentro da raiz autorizada. "
        "Usa '.' para listar a raiz e um caminho relativo para uma subpasta."
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
    if not isinstance(path, str) or not path.strip():
        return {"erro": "O argumento pasta tem de ser um caminho relativo."}
    relative = Path(path)
    if relative.anchor:
        return {"erro": "O argumento pasta tem de ser um caminho relativo."}
    try:
        folder = (root / relative).resolve()
        folder.relative_to(root)
        names = sorted(
            entry.name for entry in folder.iterdir()
            if entry.resolve().is_relative_to(root) and entry.is_file()
        )
        return {"ficheiros": names}
    except (KeyError, TypeError, ValueError, OSError, RuntimeError):
        return {"erro": "Pasta fora da área autorizada ou indisponível."}


def respond(request, root):
    method = request["method"]
    params = request.get("params", {})
    if "id" not in request:
        return None
    reply = {"jsonrpc": "2.0", "id": request["id"]}
    if method == "initialize":
        reply["result"] = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "jarvis-files", "version": "0.1.0"},
        }
    elif method == "ping":
        reply["result"] = {}
    elif method == "tools/list":
        reply["result"] = {"tools": [LIST_FILES]}
    elif method == "tools/call" and params.get("name") == LIST_FILES["name"]:
        result = list_files(root, params.get("arguments", {}))
        reply["result"] = {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "isError": "erro" in result,
        }
    else:
        reply["error"] = {"code": -32601, "message": "Método ou ferramenta desconhecida."}
    return reply


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root.resolve(strict=True)
    if not root.is_dir():
        parser.error("A pasta autorizada tem de ser um diretório.")
    for line in sys.stdin.buffer:
        try:
            request = json.loads(line)
            reply = respond(request, root)
        except (ValueError, TypeError, KeyError, AttributeError):
            reply = {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32600, "message": "Pedido JSON-RPC inválido.",
            }}
        if reply is not None:
            print(json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
