"""Transcrição no próprio computador; o modelo é preparado separadamente."""
import io
import os
from pathlib import Path
from threading import Lock

_lock = Lock()
_model = None


def model_path():
    return Path(os.environ.get('JARVIS_WHISPER_MODEL', Path.home() / '.jarvis-portatil' / 'models' / 'whisper-small'))


def transcribe(audio):
    global _model
    if not audio or len(audio) > 8 * 1024 * 1024:
        raise ValueError('Grava entre um instante e 60 segundos de voz.')
    if not (model_path() / 'model.bin').is_file():
        raise ValueError('Prepara o ditado local com python -m scripts.setup_voice.')
    if not _lock.acquire(blocking=False):
        raise ValueError('Já está uma transcrição em curso. Aguarda antes de repetir.')
    try:
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
        samples = decode_audio(io.BytesIO(audio), sampling_rate=16000)
        if len(samples) > 61 * 16000:
            raise ValueError('O ditado está limitado a 60 segundos.')
        if _model is None:
            _model = WhisperModel(str(model_path()), device='cpu', compute_type='int8', local_files_only=True)
        segments, _ = _model.transcribe(samples, language='pt', beam_size=5, vad_filter=True,
                                       initial_prompt='Transcrição em português de Portugal.',
                                       condition_on_previous_text=False)
        return ' '.join(segment.text.strip() for segment in segments).strip()[:8000]
    finally:
        _lock.release()
