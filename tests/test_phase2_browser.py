"""Testes de interface; áudio simulado não substitui o ensaio físico."""
import json
import os
import tempfile
import threading
import time
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from jarvis.app import Handler


class Phase2BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.environment = patch.dict(os.environ, {'JARVIS_DATA_DIR':cls.directory.name})
        cls.environment.start()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, key=None))
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        cls.environment.stop()
        cls.directory.cleanup()

    def setUp(self):
        self.page = self.browser.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])

    def submit(self, text):
        self.page.locator('#prompt').fill(text)
        self.page.locator('#prompt').press('Enter')
        self.page.wait_for_function("!document.querySelector('.submit').disabled")

    def test_reminder_correction_cancel_and_single_delivery(self):
        page = self.page
        page.goto(self.base)
        page.clock.install()
        self.submit('Lembra-me daqui a 3 segundos de pausa')
        self.submit('afinal, daqui a 1 segundo')
        page.clock.fast_forward(1500)
        self.assertEqual(page.locator('#reminders > p').count(), 1)
        page.clock.fast_forward(4000)
        self.assertEqual(page.locator('#reminders > p').count(), 1)
        page.clock.set_system_time(time.time())
        self.submit('Lembra-me daqui a 3 segundos de outro aviso')
        self.submit('Cancela o último lembrete')
        page.clock.fast_forward(4000)
        self.assertEqual(page.locator('#reminders > p').count(), 1)

    def test_keyboard_speech_interrupt_clears_queue(self):
        page = self.page
        page.add_init_script('''
          window.spoken=[]; window.cancels=0;
          window.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
          Object.defineProperty(window, 'speechSynthesis', {value:{
            getVoices:()=>[{localService:true, lang:'pt-PT', name:'Teste', voiceURI:'teste'}],
            addEventListener:()=>{}, speak:s=>{window.spoken.push(s.text);s.onstart?.();},
            cancel:()=>window.cancels++}});
        ''')
        page.goto(self.base)
        page.evaluate("queueSpeech('Primeira frase longa.'); queueSpeech('Segunda frase.');")
        self.assertTrue(page.locator('#stop-speech').is_visible())
        page.keyboard.press('Escape')
        self.assertTrue(page.locator('#stop-speech').is_hidden())
        self.assertEqual(page.evaluate('speaking.size'), 0)
        self.assertEqual(page.evaluate('window.cancels'), 1)
        self.assertTrue(page.locator('#speech-caption').is_hidden())

    def test_keyboard_dictation_and_track_release(self):
        page = self.page
        page.add_init_script('''
          window.stopped=0;
          window.SpeechRecognition=undefined; window.webkitSpeechRecognition=undefined;
          navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[{stop:()=>window.stopped++}]});
          window.MediaRecorder=class {
            state='inactive'; start(){this.state='recording';}
            stop(){this.state='inactive';this.ondataavailable({data:new Blob(['test'])});this.onstop();}
          };
        ''')
        page.route('**/transcribe', lambda route: route.fulfill(json={'text':'Consulta a bateria'}))
        page.goto(self.base)
        page.keyboard.press('Alt+Shift+D')
        page.wait_for_function("document.querySelector('#microphone-status').textContent==='Microfone ativo'")
        page.keyboard.press('Alt+Shift+D')
        page.wait_for_function("document.querySelector('#prompt').value==='Consulta a bateria'")
        self.assertGreater(page.evaluate('window.stopped'), 0)
        self.assertEqual(page.locator('#microphone-status').inner_text(), 'Microfone inativo')
        page.locator('#prompt').press('Enter')
        page.wait_for_function("!document.querySelector('.submit').disabled")
        self.assertIn('Bateria:', page.locator('#messages').inner_text())

    def test_microphone_denied_keeps_draft_and_text_available(self):
        page = self.page
        page.add_init_script('''
          window.SpeechRecognition=undefined; window.webkitSpeechRecognition=undefined;
          navigator.mediaDevices.getUserMedia=async()=>{throw new Error('denied');};
        ''')
        page.goto(self.base)
        page.locator('#prompt').fill('rascunho')
        page.locator('#dictate').click()
        page.wait_for_function("document.querySelector('#voice-status').textContent.includes('Permite')")
        self.assertEqual(page.locator('#prompt').input_value(), 'rascunho')
        self.assertTrue(page.locator('.submit').is_enabled())
        self.assertTrue(page.locator('#dictate').is_enabled())

    def test_unavailable_integration_does_not_block_local_requests(self):
        page = self.page
        page.goto(self.base)
        self.submit('Explica a fotossíntese')
        self.assertIn('Hermes', page.locator('#notice').inner_text())
        self.submit('Consulta agenda hoje')
        self.assertIn('agenda local', page.locator('#messages').inner_text())
