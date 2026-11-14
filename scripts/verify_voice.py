"""Ensaiar captura de um WAV no navegador e transcrição local sem ligações externas.

O WAV é uma entrada de teste, não o microfone físico do utilizador.
"""
import argparse
import os
import socket
import tempfile
import threading
import time
import wave
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from jarvis.app import Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wav', type=Path)
    args = parser.parse_args()
    with wave.open(str(args.wav)) as sample:
        seconds = sample.getnframes() / sample.getframerate()
    original_connect = socket.socket.connect

    def local_connect(connection, address):
        if address[0] not in {'127.0.0.1', '::1'}:
            raise OSError('Ligação externa bloqueada no teste de voz.')
        return original_connect(connection, address)

    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'JARVIS_DATA_DIR':directory}), \
            patch.object(socket.socket, 'connect', local_connect):
        with ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, key=None)) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(args=[
                        '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
                        f'--use-file-for-fake-audio-capture={args.wav.resolve()}%noloop',
                    ])
                    page = browser.new_page()
                    page.add_init_script('window.SpeechRecognition=undefined; window.webkitSpeechRecognition=undefined;')
                    page.goto(f'http://127.0.0.1:{server.server_port}')
                    page.keyboard.press('Alt+Shift+D')
                    page.wait_for_function("document.querySelector('#microphone-status').textContent==='Microfone ativo'")
                    page.wait_for_timeout((seconds + 1) * 1000)
                    started = time.monotonic()
                    page.keyboard.press('Alt+Shift+D')
                    page.wait_for_function("!document.querySelector('#dictate').disabled", timeout=90000)
                    transcript = page.locator('#prompt').input_value()
                    assert '45 minutos' in transcript, transcript
                    assert 'Microfone inativo' in page.locator('#microphone-status').inner_text()
                    assert page.evaluate('capture === undefined')
                    print(f'Transcrição: {transcript}', flush=True)
                    print(f'Transcrição local após parar: {time.monotonic()-started:.2f} s', flush=True)
                    with page.expect_response('**/chat') as response:
                        page.locator('#prompt').press('Enter')
                    result = response.value.json()
                    assert response.value.ok and result.get('reminder'), result
                    assert 'Notas da sessão' in result['reply'], result
                    print('Comando transcrito executado: projeto, notas e lembrete.', flush=True)
                    browser.close()
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    main()
