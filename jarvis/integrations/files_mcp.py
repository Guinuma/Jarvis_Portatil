"""Ferramenta MCP de leitura para listar uma pasta autorizada."""
import argparse
import getpass
import json
import logging
import sqlite3
import sys
from contextlib import closing
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


METADATA = {
    "name": "consultar_metadados",
    "description": "Consultar nome, tamanho e data de alteração de um ficheiro dentro da raiz autorizada.",
    "inputSchema": {
        "type": "object", "properties": {"ficheiro": {"type": "string", "minLength": 1}},
        "required": ["ficheiro"], "additionalProperties": False,
    },
    "annotations": {"readOnlyHint": True, "openWorldHint": False},
}
PACKAGES = {"metadados": METADATA}


def package_state(path, package=None, enabled=None):
    if path is None or (package is None and not path.is_file()):
        return set()
    with closing(sqlite3.connect(path)) as connection, connection:
        if package is not None:
            connection.execute("CREATE TABLE IF NOT EXISTS extensions (name TEXT PRIMARY KEY, enabled INTEGER NOT NULL)")
            connection.execute(
                """INSERT INTO extensions VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET enabled=excluded.enabled""",
                (package, int(enabled)),
            )
        return {row[0] for row in connection.execute("SELECT name FROM extensions WHERE enabled=1")}


def public_tools(user, policy, extensions):
    tools = [LIST_FILES]
    try:
        active = package_state(extensions)
    except (OSError, sqlite3.Error):
        active = set()
    if policy is None:
        return tools
    tools.extend(tool for name, tool in PACKAGES.items() if name in active)
    try:
        allowed = json.loads(policy.read_text(encoding="utf-8-sig")).get(user, [])
    except (OSError, ValueError, TypeError, AttributeError):
        return []
    return [tool for tool in tools if isinstance(allowed, list) and tool["name"] in allowed]


def metadata(root, arguments):
    if not isinstance(arguments, dict) or set(arguments) != {"ficheiro"}:
        return {"erro": "Indica apenas o argumento ficheiro."}
    name = arguments["ficheiro"]
    if not isinstance(name, str) or not name.strip() or len(name) > 500 or Path(name).anchor:
        return {"erro": "Indica um caminho relativo à pasta autorizada."}
    try:
        path = (root / name).resolve()
        relative = path.relative_to(root)
        if not path.is_file():
            raise ValueError
        info = path.stat()
    except (OSError, ValueError, RuntimeError):
        return {"erro": "Ficheiro indisponível na pasta autorizada."}
    return {"ficheiro": relative.as_posix(), "bytes": info.st_size,
            "alterado": datetime.fromtimestamp(info.st_mtime).astimezone().isoformat(timespec="seconds")}


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


def respond(request, root, *, user=None, policy=None, extensions=None):
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
        reply["result"] = {"tools": public_tools(user, policy, extensions)}
    elif method == "tools/call":
        name = params.get("name")
        allowed = any(name == candidate["name"] for candidate in public_tools(user, policy, extensions))
        handlers = {LIST_FILES["name"]: list_files, METADATA["name"]: metadata}
        result = handlers[name](root, params.get("arguments", {})) if allowed else {
            "erro": "Permissão recusada para esta ferramenta.",
        }
        outcome = result.get("erro")
        if not outcome:
            outcome = f'{len(result["ficheiros"])} ficheiro(s)' if "ficheiros" in result else "Metadados devolvidos."
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
    parser.add_argument("--extensions", type=Path, help="Base SQLite de extensões MCP.")
    management = parser.add_mutually_exclusive_group()
    management.add_argument("--install-extension", choices=PACKAGES, help="Instalar uma extensão integrada.")
    management.add_argument("--disable-extension", choices=PACKAGES, help="Desativar uma extensão.")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if not root.is_dir():
        parser.error("A pasta autorizada tem de ser um diretório.")
    if package := args.install_extension or args.disable_extension:
        if args.extensions is None:
            parser.error("Indica também o caminho --extensions.")
        try:
            package_state(args.extensions, package, enabled=bool(args.install_extension))
        except (OSError, sqlite3.Error):
            parser.error("Não consegui guardar a configuração das extensões.")
        return
    if args.audit:
        logging.basicConfig(filename=args.audit, encoding="utf-8", level=logging.INFO,
                            format="%(message)s")
    # A identidade vem da conta que executa o gateway, nunca dos argumentos do modelo.
    user = getpass.getuser()
    for line in sys.stdin.buffer:
        try:
            request = json.loads(line)
            reply = respond(request, root, user=user, policy=args.policy, extensions=args.extensions)
        except (ValueError, TypeError, KeyError, AttributeError):
            reply = {"jsonrpc": "2.0", "id": None, "error": {
                "code": -32600, "message": "Pedido JSON-RPC inválido.",
            }}
        if reply is not None:
            print(json.dumps(reply), flush=True)


if __name__ == "__main__":
    main()
