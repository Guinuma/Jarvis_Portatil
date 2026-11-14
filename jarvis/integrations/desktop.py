"""Consultas locais ao estado do Windows."""
import ctypes
import os
from ctypes import wintypes
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .editor import normalize
from .project_files import safe_path


class PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ac", ctypes.c_ubyte), ("flags", ctypes.c_ubyte),
        ("percent", ctypes.c_ubyte), ("saving", ctypes.c_ubyte),
        ("remaining", ctypes.c_uint32), ("full", ctypes.c_uint32),
    ]


def desktop_query(text, root):
    command = normalize(text).rstrip(".!?")
    focus = {
        "ativa o modo de foco": "focus-start",
        "desativa o modo de foco": "focus-stop",
        "consulta o modo de foco": "focus-status",
    }.get(command)
    if focus:
        state = accessibility(focus)
        return "Concentração do Windows ativa." if state == "active" else "Concentração do Windows inativa."
    selection = re.fullmatch(r'lê a seleção da janela "([^"]+)"[.!]?', text, re.I)
    if selection:
        return accessibility("selection", selection[1]) or "A janela não expôs texto selecionado."
    if command == "mostra os monitores":
        return "\n".join(
            f"Monitor {number}: {x}, {y}"
            for number, (x, y) in enumerate(monitor_positions(ctypes.windll.user32), 1)
        )
    window = re.fullmatch(r'(minimiza|maximiza|restaura|move) a janela "([^"]+)"(?: para (?:(\d+),\s*(\d+)|o monitor (\d+)))?', command)
    if window and (window[1] != "move" or window[3] or window[5]):
        return manage_window(window)
    if command in {"consulta a bateria", "estado da bateria", "mostra a bateria"}:
        power = PowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(power)):
            raise OSError("Não consegui consultar a bateria.")
        if power.percent > 100:
            return "O Windows não reportou uma bateria disponível."
        state = "a carregar" if power.flags & 8 else {0: "sem alimentação externa", 1: "ligado à corrente"}.get(power.ac, "alimentação desconhecida")
        return f"Bateria: {power.percent}% · {state}."
    drive = re.fullmatch(r"(?:consulta|mostra) (?:o )?armazenamento(?: (?:da unidade )?([a-z]):?)?", command)
    if drive:
        unit = drive[1].upper() + ":\\" if drive[1] else root.anchor
        free = shutil.disk_usage(unit).free
        return f"Espaço disponível em {unit}: {free / 1024**3:.1f} GiB."
    if command in {"le a area de transferencia", "mostra a area de transferencia"}:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); Get-Clipboard -Raw"],
            capture_output=True, encoding="utf-8", timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise OSError("Não consegui ler a área de transferência.")
        return result.stdout[:4000].strip() or "A área de transferência não tem texto."
    if command in {"faz uma captura de ecra", "captura o ecra"}:
        try:
            from PIL import ImageGrab
        except ImportError as error:
            raise ValueError("Instala Pillow para capturar o ecrã.") from error
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = safe_path(root, f"capturas/ecrã-{stamp}.png")
        target.parent.mkdir(exist_ok=True)
        image = ImageGrab.grab(all_screens=True)
        with target.open("xb") as stream:
            image.save(stream, format="PNG")
        return f"Captura guardada em {target}."
    return None


def manage_window(command):
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    matches = []

    @callback_type
    def collect(handle, _):
        if user32.IsWindowVisible(handle):
            title = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(handle, title, len(title))
            if command[2] in normalize(title.value):
                matches.append((handle, title.value))
        return True

    user32.EnumWindows(collect, 0)
    if len(matches) != 1:
        return ("Encontrei várias janelas: " + " · ".join(title for _, title in matches)
                if matches else "Não encontrei uma janela visível com esse título.")
    handle, title = matches[0]
    action = command[1]
    if action == "move":
        if command[5]:
            monitor = int(command[5])
            screens = monitor_positions(user32)
            if not 1 <= monitor <= len(screens):
                raise ValueError(f"Escolhe um monitor entre 1 e {len(screens)}.")
            x, y = screens[monitor - 1]
        else:
            x, y = int(command[3]), int(command[4])
        user32.SetWindowPos.argtypes = (
            wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT,
        )
        if not user32.SetWindowPos(handle, None, x, y, 0, 0, 0x0015):
            raise OSError("O Windows não moveu a janela.")
    else:
        user32.ShowWindow(handle, {"minimiza": 6, "maximiza": 3, "restaura": 9}[action])
    return f"Comando {action} aplicado a {title}."

def monitor_positions(user32):
    positions = []
    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )

    @callback_type
    def collect(_monitor, _dc, rect, _data):
        positions.append((rect.contents.left, rect.contents.top))
        return True

    if not user32.EnumDisplayMonitors(None, None, collect, 0):
        raise OSError("Não consegui enumerar os monitores.")
    return sorted(positions, key=lambda position: (position != (0, 0), position))

def accessibility(action, title=""):
    process = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
         str(Path(__file__).with_name("windows_accessibility.ps1")), action],
        env={**os.environ, "JARVIS_WINDOW_TITLE": title},
        capture_output=True, encoding="utf-8", errors="replace", timeout=15,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if process.returncode:
        raise OSError("Não consegui confirmar o comando de acessibilidade do Windows.")
    return process.stdout.strip()[:4000]