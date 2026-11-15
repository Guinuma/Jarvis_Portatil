"""Executar Python e unittest numa cópia de trabalho isolada por Docker."""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from threading import Thread
from uuid import uuid4

from jarvis.integrations.code_tools import git_read
from jarvis.integrations.editor import resolve_project
from jarvis.integrations.project_files import SKIP, safe_path

TESTS = re.compile(r'corre (?:os )?testes python(?: de "([^"\r\n]{1,500})")?[.!]?', re.I)
SCRIPT = re.compile(r'executa "([^"\r\n]{1,500})" em isolamento[.!]?', re.I)
SCOPE = re.compile(r'(.+?) no projeto "([^"\r\n]{1,500})"[.!]?', re.I)
IMAGE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9./_:@-]{0,159}")
PRIVATE = {"emails", "notes", "reunioes", "recibos"}
MAX_SNAPSHOT = 64 * 1024 * 1024
MAX_OUTPUT = 16000


def runner_command(text, root):
    command = re.sub(r"^jarvis,\s*", "", text, flags=re.I)
    scoped = SCOPE.fullmatch(command)
    command = scoped[1] if scoped else command
    tests, script = TESTS.fullmatch(command), SCRIPT.fullmatch(command)
    if not tests and not script:
        return None
    if scoped:
        choices = resolve_project(scoped[2], root)
        if len(choices) != 1:
            raise ValueError("Indica um projeto autorizado pelo nome ou caminho exato.")
        root = choices[0][1]
    name = script[1] if script else tests[1] or "tests"
    selected = safe_path(root, name)
    if script and (selected.suffix.lower() != ".py" or not selected.is_file()):
        raise ValueError("Indica um script Python no projeto autorizado.")
    if tests and not selected.is_dir():
        raise ValueError("Indica uma pasta de testes existente no projeto autorizado.")
    relative = selected.relative_to(root).as_posix()
    image = os.environ.get("JARVIS_DOCKER_PYTHON_IMAGE", "python:3.12-slim").strip()
    if not IMAGE.fullmatch(image):
        raise ValueError("Configura uma imagem Docker Python válida.")
    with tempfile.TemporaryDirectory(prefix="jarvis-run-") as directory:
        snapshot = Path(directory)
        snapshot.chmod(0o755)
        copied = project_snapshot(root, snapshot)
        if not (snapshot / relative).exists():
            raise ValueError("A seleção não existe na cópia dos ficheiros versionados do projeto.")
        arguments = ["--", relative] if script else ["-m", "unittest", "discover", "-s", "./" + relative]
        status, output, timed_out, cleanup = docker_run(snapshot, image, arguments)
    label = "Execução Python" if script else "Testes Python (unittest)"
    if timed_out:
        outcome = "tempo limite de 90 segundos"
    else:
        outcome = f"código de saída {status}" + (" · conclusão sem falhas reportadas" if status == 0 else "")
    notice = "" if cleanup else "\nO Docker não confirmou a remoção do contentor."
    return f"{label} · {outcome}\nCópia de {copied} ficheiro(s) · pasta só de leitura · rede desativada{notice}\n\n{output or '(sem saída)'}"


def project_snapshot(root, snapshot):
    listed = git_read(root, ["ls-files", "-z", "--"], limit=500_000)
    if "… saída truncada" in listed:
        raise ValueError("O projeto tem demasiados caminhos para preparar a cópia isolada.")
    total = count = 0
    for name in dict.fromkeys(listed.split("\x00")):
        if not name:
            continue
        local = Path(name)
        if any(part.startswith(".") or part in SKIP or part.casefold() in PRIVATE for part in local.parts):
            continue
        if local.suffix.casefold() in {".pem", ".key", ".pfx", ".sqlite", ".sqlite3", ".eml"}:
            continue
        path = safe_path(root, name)
        if path != root / local or not path.is_file() or path.is_symlink():
            continue
        size = path.stat().st_size
        if total + size > MAX_SNAPSHOT or count >= 3000:
            raise ValueError("A cópia excede 64 MB ou 3.000 ficheiros.")
        output = snapshot / local
        output.parent.mkdir(parents=True, exist_ok=True)
        with path.open("rb") as reader, output.open("xb") as writer:
            remaining = MAX_SNAPSHOT - total
            data = reader.read(remaining + 1)
            if len(data) > remaining:
                raise ValueError("A cópia excede 64 MB.")
            writer.write(data)
            total += len(data)
        # The container runs without root privileges.
        output.chmod(0o644)
        count += 1
    return count


def docker_environment():
    docker = shutil.which("docker")
    if not docker:
        raise ValueError("Instala o Docker com contentores Linux para executar Python em isolamento.")
    env = {key: value for key, value in os.environ.items() if key.upper() not in {
        "DOCKER_CONTEXT", "DOCKER_HOST", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH",
    }}
    try:
        info = subprocess.run([docker, "context", "inspect"], capture_output=True, env=env, timeout=6, check=True)
        endpoint = json.loads(info.stdout)[0]["Endpoints"]["docker"]["Host"]
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError, TypeError) as error:
        raise ValueError("Não consegui identificar o Docker local.") from error
    if endpoint not in {"unix:///var/run/docker.sock", "npipe:////./pipe/docker_engine",
                        "npipe:////./pipe/dockerDesktopLinuxEngine"}:
        raise ValueError("Seleciona o Docker local com contentores Linux para esta operação.")
    return [docker, "--host", endpoint], env


def docker_json(base, env, arguments, failure):
    try:
        result = subprocess.run([*base, *arguments], capture_output=True, env=env, timeout=12, check=True)
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        raise ValueError(failure) from error


def docker_run(snapshot, image, arguments):
    docker, env = docker_environment()
    inspected = docker_json(docker, env, ["image", "inspect", image],
                            "A imagem Python não está disponível no Docker local.")
    try:
        image_id, platform = inspected[0]["Id"], inspected[0]["Os"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("Não consegui identificar a imagem Python local.") from error
    if platform != "linux" or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("Escolhe uma imagem local de Python para Linux.")
    label = "jarvis-python-" + uuid4().hex
    mount = io.StringIO()
    csv.writer(mount, lineterminator="").writerow(("type=bind", f"src={snapshot}", "dst=/work", "readonly"))
    options = [
        "create", "--pull=never", "--name", label, "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--user", "65534:65534",
        "--pids-limit", "64", "--memory", "512m", "--cpus", "1",
        "--log-driver", "local", "--log-opt", "max-size=1m", "--log-opt", "max-file=1",
        "--tmpfs", "/tmp:size=64m,mode=1777,noexec,nosuid,nodev", "--mount", mount.getvalue(),
        "--workdir", "/work", "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "HOME=/tmp",
        "--entrypoint", "python", image_id, *arguments,
    ]
    cleanup = False
    try:
        subprocess.run([*docker, *options], env=env, capture_output=True, timeout=15, check=True)
        actual = docker_json(docker, env, ["inspect", label], "Não consegui verificar os limites do contentor.")
        verify_container(actual)
        status, output, timed_out = execute_container(docker, env, label)
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("O Docker não conseguiu preparar ou executar o contentor local.") from error
    finally:
        try:
            removed = subprocess.run([*docker, "rm", "-f", label], env=env, capture_output=True, timeout=10)
            cleanup = removed.returncode == 0
        except (OSError, subprocess.SubprocessError):
            pass
    return status, output, timed_out, cleanup


def verify_container(value):
    try:
        entry = value[0]
        limits = entry["HostConfig"]
        mounts = entry["Mounts"]
        user = entry["Config"]["User"]
        valid = (
            limits["NetworkMode"] == "none" and limits["ReadonlyRootfs"] is True and not limits["Privileged"]
            and user == "65534:65534" and len(mounts) == 1 and mounts[0]["Type"] == "bind"
            and mounts[0]["Destination"] == "/work" and mounts[0]["RW"] is False
            and limits["Memory"] == 512 * 1024 * 1024 and limits["NanoCpus"] == 1_000_000_000
            and limits["PidsLimit"] == 64 and "ALL" in (limits["CapDrop"] or [])
            and any(option in ("no-new-privileges", "no-new-privileges:true") for option in limits["SecurityOpt"] or [])
        )
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("O Docker não confirmou os limites esperados.") from error
    if not valid:
        raise ValueError("O Docker não aplicou os limites esperados. A execução não foi iniciada.")


def execute_container(docker, env, name):
    job = subprocess.Popen([*docker, "start", "-a", name], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = bytearray()
    omitted = False

    def drain():
        nonlocal omitted
        with job.stdout as stream:
            for chunk in iter(lambda: stream.read(4096), b""):
                available = max(0, MAX_OUTPUT - len(output))
                output.extend(chunk[:available])
                omitted |= len(chunk) > available

    collect = Thread(target=drain, daemon=True)
    collect.start()
    timed_out = False
    try:
        status = job.wait(timeout=90)
    except subprocess.TimeoutExpired:
        timed_out = True
        job.kill()
        status = job.wait()
    collect.join(3)
    text = output.decode("utf-8", errors="replace")
    return status, text + ("\n… saída limitada." if omitted else ""), timed_out
