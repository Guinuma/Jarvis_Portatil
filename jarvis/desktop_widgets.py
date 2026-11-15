"""Windows widget lifecycle and browser window controls."""
import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path
from secrets import token_hex
from threading import Event, Lock, Thread

from .integrations.desktop import place_window, visible_windows
from .memory import Memory

WIDGETS = {"checklist": "Checklist", "music": "Música"}


class DesktopWidgets:
    def __init__(self, root, settings, memory_path):
        self.root = root
        self.settings = settings
        self.memory_path = memory_path
        self.instance = token_hex(12)
        self.processes = {}
        self.lock = Lock()

    def update(self, name=None, enabled=None):
        with self.lock:
            self.processes = {
                key: process for key, process in self.processes.items()
                if process.poll() is None
            }
            if name is not None:
                if name not in WIDGETS or type(enabled) is not bool:
                    raise ValueError("Widget indisponível.")
                if sys.platform != "win32":
                    raise ValueError("Os widgets flutuantes estão disponíveis no Windows.")
                process = self.processes.get(name)
                if enabled and process is None:
                    self.processes[name] = subprocess.Popen(
                        [sys.executable, "-m", "jarvis.desktop_widgets", name,
                         str(self.settings), str(self.memory_path)],
                        cwd=self.root,
                        stdin=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                elif not enabled and process is not None:
                    process.stdin.close()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                    else:
                        del self.processes[name]
            return {name: name in self.processes for name in WIDGETS}

    def close(self):
        with self.lock:
            for process in self.processes.values():
                process.stdin.close()


def quick_window_action(marker, action):
    if sys.platform != "win32":
        raise ValueError("Estes controlos do Quick Chat estão disponíveis no Windows.")
    if not isinstance(marker, str) or not re.fullmatch(r"[a-f0-9]{32}", marker):
        raise ValueError("Identificador de janela inválido.")
    if action not in ("pin", "unpin", "minimize"):
        raise ValueError("Ação de janela inválida.")

    user32 = ctypes.windll.user32
    user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user32.ShowWindow.argtypes = (wintypes.HWND, ctypes.c_int)
    user32.IsIconic.argtypes = (wintypes.HWND,)
    title = re.compile(r"^Quick Chat · JARVIS \[" + marker + r"\](?:$|\s)")
    handle = None
    for _ in range(12):
        matches = []
        for candidate, caption in visible_windows(user32):
            if not title.match(caption):
                continue
            window_class = ctypes.create_unicode_buffer(128)
            if user32.GetClassNameW(candidate, window_class, len(window_class)):
                if window_class.value in {"Chrome_WidgetWin_1", "MozillaWindowClass"}:
                    matches.append(candidate)
        if len(matches) == 1:
            handle, = matches
            break
        time.sleep(0.075)
    if handle is None:
        raise OSError("Não encontrei a janela do Quick Chat. Abre-a pelo cartão Widgets.")

    if action == "minimize":
        user32.ShowWindow(handle, 6)  # SW_MINIMIZE
        if not user32.IsIconic(handle):
            raise OSError("O Windows não conseguiu recolher o Quick Chat.")
    else:
        after = -1 if action == "pin" else -2  # HWND_TOPMOST / HWND_NOTOPMOST
        flags = 0x0013  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
        if not place_window(user32, handle, after, 0, 0, flags):
            raise OSError("O Windows não conseguiu alterar a fixação do Quick Chat.")


def main():
    import tkinter as tk
    from tkinter import ttk

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("widget", choices=sorted(WIDGETS))
    parser.add_argument("settings", type=Path)
    parser.add_argument("memory_path", type=Path)
    args = parser.parse_args()

    window = tk.Tk()
    window.title(f"{WIDGETS[args.widget]} · JARVIS")
    window.minsize(340, 160)
    if args.widget == "checklist":
        window.geometry("340x330")
    position_file = args.settings / f"{args.widget}.json"

    pinned = tk.BooleanVar(value=False)
    ttk.Checkbutton(window, text="Fixar por cima das janelas", variable=pinned,
                    command=lambda: window.attributes("-topmost", pinned.get())).pack(anchor="w", padx=14, pady=(12, 0))
    music = None
    if args.widget == "music":
        from .music_widget import MusicWidget

        music = MusicWidget(window, args.settings)
    else:
        from .checklist_widget import checklist_widget

        checklist_widget(window, Memory(args.memory_path.parent, args.memory_path.stem))
    window.update_idletasks()
    user32 = ctypes.windll.user32
    user32.GetAncestor.argtypes = (wintypes.HWND, wintypes.UINT)
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user32.MonitorFromPoint.argtypes = (wintypes.POINT, wintypes.DWORD)
    user32.MonitorFromPoint.restype = wintypes.HMONITOR
    user32.IsIconic.argtypes = (wintypes.HWND,)
    handle = user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT, the Tk frame
    last_position = None

    try:
        x, y = json.loads(position_file.read_text(encoding="utf-8"))
        if type(x) is int and type(y) is int and abs(x) < 32768 and abs(y) < 32768:
            if user32.MonitorFromPoint(wintypes.POINT(x + 24, y + 24), 0):
                place_window(user32, handle, None, x, y, 0x0015)
    except (OSError, ValueError, TypeError):
        pass

    def remember_position(event=None):
        nonlocal last_position
        if event is not None and event.widget is not window:
            return
        rect = wintypes.RECT()
        if not user32.IsIconic(handle) and user32.GetWindowRect(handle, ctypes.byref(rect)):
            last_position = (rect.left, rect.top)

    window.bind("<Configure>", remember_position, add="+")
    remember_position()
    closing = Event()

    def watch_parent():
        os.read(sys.stdin.fileno(), 1)
        closing.set()

    def close():
        remember_position()
        if last_position is not None:
            try:
                position_file.parent.mkdir(parents=True, exist_ok=True)
                position_file.write_text(json.dumps(last_position), encoding="utf-8")
            except OSError:
                pass
        if music is not None:
            music.close()
        window.destroy()

    def check_parent():
        if closing.is_set():
            close()
        else:
            window.after(200, check_parent)

    window.protocol("WM_DELETE_WINDOW", close)
    Thread(target=watch_parent, daemon=True).start()
    check_parent()
    window.mainloop()


if __name__ == "__main__":
    main()
