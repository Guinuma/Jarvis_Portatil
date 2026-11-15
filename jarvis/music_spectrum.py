"""Analyse a local track off the widget's UI thread."""
from threading import Event, Lock, Thread

INTERVAL_MS = 100
SAMPLE_RATE = 16_000
FRAME_SIZE = SAMPLE_RATE * INTERVAL_MS // 1000
BAND_COUNT = 18


class TrackSpectrum:
    def __init__(self, path):
        self.stop = Event()
        self.lock = Lock()
        self.levels = bytearray()
        self.finished = False
        self.error = ""
        Thread(target=self.analyse, args=(path,), daemon=True).start()

    def frame_at(self, milliseconds):
        offset = (milliseconds // INTERVAL_MS) * BAND_COUNT
        with self.lock:
            frame = self.levels[offset:offset + BAND_COUNT]
            return frame, self.finished, self.error

    def analyse(self, path):
        try:
            import av
            import numpy as np
        except ImportError:
            with self.lock:
                self.finished = True
                self.error = "Instala as dependências do JARVIS para mostrar o espectro."
            return

        error = ""
        try:
            edges = np.geomspace(40, 7800, BAND_COUNT + 1)
            indices = np.searchsorted(np.fft.rfftfreq(FRAME_SIZE, 1 / SAMPLE_RATE), edges)
            bands = [slice(left, max(left + 1, right)) for left, right in zip(indices[:-1], indices[1:])]
            taper = np.hanning(FRAME_SIZE)
            scale = 2 / taper.sum()

            def append_frame(samples):
                amplitude = abs(np.fft.rfft(samples * taper)) * scale
                magnitudes = np.array([amplitude[band].max() for band in bands])
                decibels = 20 * np.log10(np.maximum(magnitudes, 1e-6))
                values = np.clip((decibels + 65) / 55, 0, 1)
                with self.lock:
                    self.levels.extend((values * 255).astype(np.uint8).tobytes())

            pending = np.empty(0, dtype=np.float32)
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=SAMPLE_RATE)
            with av.open(str(path)) as audio:
                for decoded in audio.decode(audio=0):
                    if self.stop.is_set():
                        return
                    for frame in resampler.resample(decoded):
                        pending = np.concatenate((pending, frame.to_ndarray().ravel()))
                        while len(pending) >= FRAME_SIZE:
                            append_frame(pending[:FRAME_SIZE])
                            pending = pending[FRAME_SIZE:]
                for frame in resampler.resample(None):
                    pending = np.concatenate((pending, frame.to_ndarray().ravel()))
                while len(pending) >= FRAME_SIZE:
                    append_frame(pending[:FRAME_SIZE])
                    pending = pending[FRAME_SIZE:]
                if len(pending):
                    append_frame(np.pad(pending, (0, FRAME_SIZE - len(pending))))
        except (av.FFmpegError, OSError, ValueError, IndexError):
            error = "Espectro indisponível para esta faixa."
        finally:
            with self.lock:
                self.finished = True
                self.error = error
