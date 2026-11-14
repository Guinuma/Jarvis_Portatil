"""Comandos locais para abrir aplicações e sites no Windows."""
import os
import re
import shutil
import subprocess
import webbrowser
from urllib.parse import urlsplit

APPS = {
    "bloco de notas": ("notepad.exe",),
    "calculadora": ("calc.exe",),
    "explorador": ("explorer.exe",),
    "paint": ("mspaint.exe",),
}


def windows_command(text):
    match = re.fullmatch(r"(?:jarvis[, ]+)?abre (?:o )?site (\S+)", text, re.I)
    if match:
        address = match[1]
        if "://" not in address:
            address = "https://" + address
        parsed = urlsplit(address)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username is not None:
            raise ValueError("Indica um endereço HTTP ou HTTPS válido.")
        if not webbrowser.open(address):
            raise OSError("Não consegui abrir o navegador predefinido.")
        return f"Pedi ao navegador para abrir {address}."

    match = re.fullmatch(r"(?:jarvis[, ]+)?abre (?:a |o )?(?:aplicação )?(.+?)[.!?]?", text, re.I)
    if not match:
        return None
    name = match[1].casefold()
    if name not in APPS:
        return None
    command = APPS[name]
    executable = shutil.which(command[0], path=os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"))
    if not executable:
        raise OSError(f"A aplicação {name} está indisponível.")
    subprocess.Popen([executable, *command[1:]])
    return f"Pedi ao Windows para abrir {name}."
