"""Pesquisa de código e consultas Git de leitura em projetos autorizados."""
import json
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
    "historico": ["log", "-12", "--oneline", "--no-decorate", "--no-color", "--no-show-signature"],
    "ramo": ["rev-parse", "--abbrev-ref", "HEAD"],
}
DIFF = ["diff", "--no-color", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all"]
PR = re.compile(
    r'prepara (?:um )?pull request(?: para "([A-Za-z0-9][A-Za-z0-9._/-]{0,119})")?(?: com (.+))?[.!]?',
    re.I | re.S,
)


def code_command(text, root):
    scoped = re.fullmatch(r'(.+?) no projeto "([^"]+)"[.!]?', text, re.I)
    command = scoped[1] if scoped else text
    match = re.fullmatch(r'(?:procura|pesquisa) (?:no )?código "([^"]+)"[.!]?', command, re.I)
    git = re.fullmatch(r'(estado|historico|ramo|diff) (?:do )?git', normalize(command).rstrip(".!?"))
    proposal = PR.fullmatch(command)
    if not match and not git and not proposal:
        return None
    if scoped:
        projects = resolve_project(scoped[2], root)
        if len(projects) != 1:
            raise ValueError("Indica o caminho exato de um projeto autorizado.")
        root = projects[0][1]
    if not root.is_dir():
        raise ValueError("O projeto autorizado está indisponível.")
    if proposal:
        return pull_request_draft(root, proposal[1] or "origin/main", proposal[2])
    if git:
        action = git[1]
        if action == "diff":
            unstaged = diff_summary(root, [])
            staged = diff_summary(root, ["--cached"])
            return f"Alterações por preparar\n{unstaged}\n\nAlterações preparadas\n{staged}"
        return git_read(root, GIT_COMMANDS[action], limit=6000) or "Sem resultados."
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


def diff_summary(root, options):
    output = git_read(root, [*DIFF, *options, "--stat", "--patch", "--unified=0", "--", "."], limit=22_000)
    if not output:
        return "Sem alterações em ficheiros versionados."
    lines = []
    previous = []
    files = hunks = entries = 0
    for line in output.splitlines():
        if line.startswith("diff --git "):
            files += 1
            hunks = entries = 0
            previous = []
            if files > 6:
                lines.append("São apresentados excertos dos primeiros seis ficheiros.")
                break
        elif not files:
            if len(lines) < 16:
                lines.append(line)
        elif line.startswith(("--- ", "+++ ")):
            previous.append(line[:200])
        elif line.startswith("@@"):
            hunks += 1
            entries = 0
            if hunks == 1:
                lines.extend(["", *previous])
            if hunks <= 2:
                lines.append(line[:200])
            elif hunks == 3:
                lines.append("… outras zonas alteradas neste ficheiro")
        elif 0 < hunks <= 2 and line.startswith(("+", "-")):
            entries += 1
            if entries <= 3:
                lines.append(line[:180])
            elif entries == 4:
                lines.append("… outras linhas neste excerto")
        elif line == "… saída truncada":
            lines.append(line)
    return "\n".join(lines)


def pull_request_draft(root, base, raw):
    values = json.loads(raw) if raw else {}
    limits = {"título": 160, "testes": 1200}
    if (not isinstance(values, dict) or set(values) - set(limits)
            or any(not isinstance(value, str) or not 0 < len(value.strip()) <= limits[key]
                   for key, value in values.items())):
        raise ValueError('Usa {"título":"Título","testes":"Resultados que verificaste"}.')
    title = values.get("título", "").strip()
    if "\n" in title or "\r" in title:
        raise ValueError("Escreve o título numa única linha.")
    try:
        base_commit = git_read(root, ["rev-parse", "--verify", "--end-of-options", base + "^{commit}"], limit=64)
    except ValueError as error:
        raise ValueError(f"Verifica se a referência de base {base} existe no repositório autorizado.") from error
    branch = git_read(root, GIT_COMMANDS["ramo"], limit=120)
    commits = git_read(
        root, ["log", "--no-color", "--no-show-signature", "--format=%h %s", "-12", f"{base_commit}..HEAD"],
        limit=2600,
    )
    if not commits:
        return f"Não há commits para propor de {branch} para {base}."
    files = git_read(root, [*DIFF, "--name-status", f"{base_commit}...HEAD", "--", "."], limit=3200)
    subject = title or commits.splitlines()[0].partition(" ")[2][:160]
    testing = values.get("testes", "Sem resultados de testes fornecidos.").strip()
    return f"""# {subject}

Origem: {branch}
Base: {base}

## Alterações nos commits
{format_lines(commits)}

## Ficheiros afetados
{format_lines(files) if files else "- Sem diferenças de ficheiros relativamente à base comum."}

## Testes
{testing}

Rascunho local para revisão. A comparação inclui commits e deixa as alterações de trabalho para um commit posterior."""


def format_lines(text):
    return "\n".join(f"- {line}" for line in text.splitlines())


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
