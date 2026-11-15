"""Local MP3 playback for the Windows desktop widget."""
import ctypes
from pathlib import Path
from tkinter import Canvas, StringVar, filedialog, ttk

from .music_spectrum import BAND_COUNT, INTERVAL_MS, TrackSpectrum


class MP3Playback:
    def __init__(self):
        driver = ctypes.WinDLL("winmm")
        self.send = driver.mciSendStringW
        self.send.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        self.send.restype = ctypes.c_uint
        self.opened = False

    def command(self, command):
        output = ctypes.create_unicode_buffer(256)
        if self.send(command, output, len(output), None):
            raise OSError("O Windows não conseguiu reproduzir esta faixa.")
        return output.value

    def open(self, path):
        self.close()
        self.command(f'open "{path}" type mpegvideo alias jarvis_music')
        self.opened = True
        self.command("set jarvis_music time format milliseconds")
        return int(self.command("status jarvis_music length"))

    def close(self):
        if self.opened:
            self.send("close jarvis_music", None, 0, None)
            self.opened = False


def track_metadata(path):
    try:
        import av
    except ImportError:
        return path.stem, ""
    try:
        with av.open(str(path)) as audio:
            tags = {key.casefold(): value.strip() for key, value in audio.metadata.items()}
            return tags.get("title") or path.stem, tags.get("artist") or ""
    except (OSError, ValueError, av.FFmpegError):
        return path.stem, ""


def time_label(milliseconds):
    minutes, seconds = divmod(milliseconds // 1000, 60)
    return f"{minutes}:{seconds:02}"


class MusicWidget:
    def __init__(self, window, settings):
        self.window = window
        self.folder_file = settings / "music-folder.txt"
        self.player = MP3Playback()
        self.analysis = None
        self.spectrum_frame = None
        self.folder = Path.home() / "Music" / "para mp3"
        try:
            saved = self.folder_file.read_text(encoding="utf-8").strip()
            if saved:
                self.folder = Path(saved)
        except (OSError, ValueError):
            pass
        self.tracks = []
        self.index = 0
        self.length = 0
        self.position = 0
        self.playing = False
        self.title = StringVar(value="Música local")
        self.artist = StringVar()
        self.clock = StringVar(value="0:00 / 0:00")
        self.feedback = StringVar()
        self.folder_label = StringVar()

        frame = ttk.Frame(window, padding=14)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, textvariable=self.title, wraplength=310,
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.artist, wraplength=310).pack(anchor="w")
        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.pack(fill="x", pady=(10, 3))
        self.progress.bind("<Button-1>", self.seek)
        ttk.Label(frame, textvariable=self.clock).pack(anchor="e")
        transport = ttk.Frame(frame)
        transport.pack(fill="x", pady=8)
        self.previous = ttk.Button(transport, text="Anterior", command=lambda: self.skip(-1))
        self.previous.pack(side="left")
        self.toggle = ttk.Button(transport, text="Reproduzir", command=self.toggle_playback)
        self.toggle.pack(side="left", padx=4)
        self.next = ttk.Button(transport, text="Seguinte", command=lambda: self.skip(1))
        self.next.pack(side="left")
        ttk.Button(frame, text="Escolher pasta", command=self.choose_folder).pack(anchor="w")
        ttk.Label(frame, textvariable=self.folder_label, wraplength=310).pack(anchor="w", pady=(4, 0))
        ttk.Label(frame, textvariable=self.feedback, wraplength=310).pack(anchor="w")
        self.expand = ttk.Button(frame, text="Mostrar fila e espectro", command=self.toggle_queue)
        self.expand.pack(anchor="w", pady=(8, 0))
        self.queue_frame = ttk.Frame(frame)
        self.spectrum = Canvas(self.queue_frame, height=76, background="#121e34", highlightthickness=0)
        self.spectrum.pack(fill="x", pady=(0, 8))
        self.spectrum.bind("<Configure>", lambda event: self.draw_spectrum())
        queue_body = ttk.Frame(self.queue_frame)
        queue_body.pack(fill="both", expand=True)
        self.queue = ttk.Treeview(queue_body, show="tree", selectmode="browse", height=5)
        scrollbar = ttk.Scrollbar(queue_body, orient="vertical", command=self.queue.yview)
        self.queue.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.queue.pack(side="left", fill="both", expand=True)
        self.queue.column("#0", width=280, stretch=True)
        self.queue.bind("<Double-1>", self.play_selected)
        self.queue.bind("<Return>", self.play_selected)
        self.load_folder()
        self.tick()

    def choose_folder(self):
        chosen = filedialog.askdirectory(parent=self.window, initialdir=self.folder if self.folder.is_dir() else Path.home())
        if not chosen:
            return
        self.folder = Path(chosen)
        self.load_folder()
        try:
            self.folder_file.parent.mkdir(parents=True, exist_ok=True)
            self.folder_file.write_text(str(self.folder), encoding="utf-8")
        except OSError:
            self.feedback.set("A pasta está ativa nesta sessão. Não consegui guardar a escolha.")

    def load_folder(self):
        self.close()
        self.playing = False
        self.length = self.position = self.index = 0
        self.folder_label.set(str(self.folder))
        self.feedback.set("")
        try:
            self.tracks = sorted(
                (item for item in self.folder.rglob("*") if item.suffix.casefold() == ".mp3" and item.is_file()),
                key=lambda item: str(item).casefold(),
            )
        except OSError:
            self.tracks = []
        if children := self.queue.get_children():
            self.queue.delete(*children)
        for index, path in enumerate(self.tracks):
            self.queue.insert("", "end", iid=str(index), text=str(path.relative_to(self.folder)))
        if self.tracks:
            self.select(0)
        else:
            self.title.set("Sem faixas MP3")
            self.artist.set("")
            self.feedback.set("Escolhe uma pasta com ficheiros MP3.")
        self.update_controls()

    def select(self, index):
        self.index = index
        title, artist = track_metadata(self.tracks[index])
        self.title.set(title)
        self.artist.set(artist)
        self.queue.selection_set(str(index))
        self.queue.see(str(index))

    def update_controls(self):
        self.progress.configure(maximum=max(1, self.length), value=self.position)
        self.clock.set(f"{time_label(self.position)} / {time_label(self.length)}")
        self.toggle.configure(text="Pausa" if self.playing else "Reproduzir",
                              state="normal" if self.tracks else "disabled")
        self.previous.configure(state="normal" if self.index > 0 else "disabled")
        self.next.configure(state="normal" if self.index + 1 < len(self.tracks) else "disabled")

    def playback_error(self, error):
        self.close()
        self.playing = False
        self.position = self.length = 0
        self.feedback.set(str(error))
        self.update_controls()

    def play(self, index):
        self.feedback.set("")
        self.select(index)
        try:
            self.length = self.player.open(self.tracks[index])
            self.position = 0
            self.player.command("play jarvis_music from 0")
            self.playing = True
            self.refresh_spectrum()
        except (OSError, ValueError) as error:
            self.playback_error(error)
        self.update_controls()

    def skip(self, step):
        index = self.index + step
        if 0 <= index < len(self.tracks):
            self.play(index)

    def toggle_playback(self):
        if not self.tracks:
            return
        if not self.player.opened or self.position >= self.length:
            self.play(self.index)
            return
        try:
            if self.playing:
                self.player.command("pause jarvis_music")
                self.position = int(self.player.command("status jarvis_music position"))
            else:
                self.player.command(f"play jarvis_music from {self.position}")
            self.playing = not self.playing
        except (OSError, ValueError) as error:
            self.playback_error(error)
        self.update_controls()

    def seek(self, event):
        if not self.player.opened or not self.length:
            return
        ratio = max(0, min(1, event.x / self.progress.winfo_width()))
        position = min(self.length - 1, round(ratio * self.length))
        try:
            self.player.command(f"seek jarvis_music to {position}")
            if self.playing:
                self.player.command(f"play jarvis_music from {position}")
            self.position = position
        except OSError as error:
            self.playback_error(error)
        self.update_controls()

    def tick(self):
        if self.playing:
            try:
                self.position = int(self.player.command("status jarvis_music position"))
                if self.player.command("status jarvis_music mode") == "stopped":
                    self.playing = False
                    if self.index + 1 < len(self.tracks):
                        self.skip(1)
                    else:
                        self.position = self.length
            except (OSError, ValueError) as error:
                self.playback_error(error)
            self.update_controls()
        self.draw_spectrum()
        self.window.after(INTERVAL_MS, self.tick)

    def toggle_queue(self):
        if self.queue_frame.winfo_manager():
            self.queue_frame.pack_forget()
            self.expand.configure(text="Mostrar fila e espectro")
        else:
            self.queue_frame.pack(fill="both", expand=True, pady=(8, 0))
            if self.tracks:
                self.queue.see(str(self.index))
            self.expand.configure(text="Recolher fila e espectro")
        self.refresh_spectrum()

    def stop_analysis(self):
        if self.analysis is not None:
            self.analysis.stop.set()
            self.analysis = None

    def close(self):
        self.player.close()
        self.stop_analysis()

    def refresh_spectrum(self):
        self.stop_analysis()
        if self.queue_frame.winfo_manager() and self.player.opened:
            self.analysis = TrackSpectrum(self.tracks[self.index])
        self.draw_spectrum()

    def draw_spectrum(self):
        if not self.queue_frame.winfo_manager():
            return
        width, height = self.spectrum.winfo_width(), self.spectrum.winfo_height()
        message = ""
        levels = []
        if self.analysis is None:
            message = "Reproduz uma faixa para ver o espectro."
        elif self.position < self.length:
            levels, finished, message = self.analysis.frame_at(self.position)
            if not levels and not finished:
                message = "A preparar o espectro…"
        frame = (width, height, levels, message)
        if frame == self.spectrum_frame:
            return
        self.spectrum_frame = frame
        self.spectrum.delete("all")
        if message:
            self.spectrum.create_text(width / 2, height / 2, text=message, fill="#dce9ff",
                                      width=max(1, width - 16))
            return
        step = max(1, width - 20) / BAND_COUNT
        for index, level in enumerate(levels or [0] * BAND_COUNT):
            left = 10 + index * step
            bar_height = max(2, level / 255 * max(2, height - 16))
            self.spectrum.create_rectangle(left, height - 8 - bar_height, left + step * 0.68, height - 8,
                                           fill="#73d8ef", width=0)

    def play_selected(self, event):
        if selected := self.queue.selection():
            self.play(int(selected[0]))
