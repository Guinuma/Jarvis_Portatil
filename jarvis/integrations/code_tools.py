"""Pesquisa de código e consultas Git de leitura em projetos autorizados."""
import os
import re
import subprocess
from pathlib import Path

from .editor import normalize, resolve_project
from .project_files import SKIP

CODE_TYPES = {".py", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".java", ".c", ".cpp",
              ".h", ".hpp", ".cs", ".rs", ".go", ".gd", ".sql", ".sh", ".ps1", ".json", ".toml", ".yaml", ".yml"}
GIT_COMMANDS = {
    "estado": ["status", "--short", "--branch", "--ignore-submodules=all"],
    "historico": ["log", "-12", "--oneline", "--no-decorate"],
    "ramo": ["rev-parse", "--abbrev-ref", "HEAD"],
    "diff": ["diff", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all", "--stat", "--", "."],
}


def code_command(text, root):
    scoped = re.fullmatch(r'(.+?) no projeto "([^"]+)"[.!]?', text, re.I)
    command = scoped[1] if scoped else text
    match = re.fullmatch(r'(?:procura|pesquisa) (?:no )?código "([^"]+)"[.!]?', command, re.I)
    git = re.fullmatch(r'(estado|historico|ramo|diff) (?:do )?git', normalize(command).rstrip(".!?"))
    if not match and not git:
        return None
    if scoped:
        projects = resolve_project(scoped[2], root)
        if len(projects) != 1:
            raise ValueError("Indica o caminho exato de um projeto autorizado.")
        root = projects[0][1]
    if not root.is_dir():
        raise ValueError("O projeto autorizado está indisponível.")
    if git:
        action = git[1]
        output = git_read(root, GIT_COMMANDS[action], limit=6000)
        if action == "diff":
            staged = git_read(root, [*GIT_COMMANDS["diff"][:1], "--cached", *GIT_COMMANDS["diff"][1:]], limit=6000)
            return f"Alterações por preparar\n{output or 'Sem alterações.'}\n\nAlterações preparadas\n{staged or 'Sem alterações.'}"
        return output or "Sem resultados."
    query = match[1].strip().casefold()
    if not query:
        raise ValueError("Indica o texto que queres encontrar no código.")
    results = []
    for folder, dirs, names in os.walk(root):
        parent = Path(folder)
        dirs[:] = sorted(name for name in dirs if name not in SKIP and not name.startswith(".")
                         and (parent / name).resolve().parent == parent)
        for name in sorted(names):
            path = parent / name
            if (path.suffix.lower() not in CODE_TYPES or name.startswith(".") or path.is_symlink()
                    or path.resolve().parent != parent):
                continue
            try:
                with path.open(encoding="utf-8-sig", errors="replace") as source:
                    for number, line in enumerate(source.read(256_000).splitlines(), 1):
                        if query in line.casefold():
                            results.append(f"{path.relative_to(root).as_posix()}:{number} — {line.strip()[:220]}")
                        if len(results) == 20:
                            return "\n".join(results)
            except OSError:
                continue
    return "\n".join(results) or "Não encontrei esse texto no código do projeto."


def git_read(root, arguments, limit):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    base = ["git", "--no-pager", "-c", "core.fsmonitor=false", "-C", str(root)]
    try:
        top = subprocess.run([*base, "rev-parse", "--show-prefix"], env=env, capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=8)
        if top.returncode or top.stdout.strip():
            raise ValueError("A raiz autorizada tem de corresponder à raiz do repositório Git.")
        result = subprocess.run([*base, *arguments], env=env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=8)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Git indisponível ou consulta demasiado demorada.") from error
    if result.returncode:
        raise ValueError("O Git não conseguiu concluir a consulta.")
    output = result.stdout.strip()
    return output[:limit] + ("\n… saída truncada" if len(output) > limit else "")
