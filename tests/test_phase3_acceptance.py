"""Teste de aceitação de memória e rotinas com uma pasta temporária."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from urllib.request import Request, urlopen

from jarvis import app
from jarvis.routines import run_due
from scripts.backup_memory import copy_database


class Phase3Acceptance(unittest.TestCase):
    def test_combined_request_restore_and_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            note = root / "notes" / "2026-11-14" / "sessao.md"
            note.parent.mkdir(parents=True)
            note.write_text("Notas sobre temporizadores.", encoding="utf-8")
            with patch.dict(os.environ, {"JARVIS_DATA_DIR": str(root / "state"), "JARVIS_PROFILE": "acceptance"}), \
                    patch.object(app, "ROOT", root):
                self.check_flow(root, note)

    def check_flow(self, root, note):
        with ThreadingHTTPServer(("127.0.0.1", 0), partial(app.Handler, key=None)) as server:
            thread = Thread(target=server.serve_forever)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def post(path, data):
                request = Request(base + path, json.dumps(data).encode(), {
                    "Origin": base, "Content-Type": "application/json",
                })
                with urlopen(request, timeout=5) as result:
                    return json.load(result)

            def chat(text):
                return post("/chat", {"messages": [{"role": "user", "content": text}]})["reply"]

            try:
                answer = chat(
                    "Lembra-te de que o meu projeto principal é o JARVIS. "
                    "Encontra a nota onde escrevi sobre temporizadores e, amanhã às nove, ativa o modo programação."
                )
                self.assertIn("sessao.md", answer)
                self.assertIn("09:00", answer)
                saved = post("/memory", {"action": "list"})
                self.assertEqual(saved["records"][0]["value"], "JARVIS")
                self.assertEqual(saved["records"][0]["source"], "Conversa")
                post("/memory", {
                    "action": "save", "name": "projeto principal", "kind": "projeto", "value": "JARVIS Portátil",
                })
                post("/memory", {"action": "settings", "voice": "pt", "speed": "0.8", "automatic": True})
                with patch("jarvis.integrations.project_files.open_project") as open_note:
                    chat('Abre o ficheiro "notes/2026-11-14/sessao.md"')
                    open_note.assert_called_once_with(root, target=note)
            finally:
                server.shutdown()
                thread.join()

        memory = app.local_memory()
        backup = root / "backup.sqlite3"
        copy_database(memory.path, backup)
        with patch.dict(os.environ, {"JARVIS_PROFILE": "restored"}):
            restored = app.local_memory()
            copy_database(backup, restored.path)
        self.assertEqual(restored.list()[0]["value"], "JARVIS Portátil")
        self.assertEqual(json.loads(restored.execute("SELECT value FROM settings")[0]["value"])["speed"], "0.8")
        task = restored.execute("SELECT * FROM routines")[0]
        tomorrow = datetime.now().date() + timedelta(days=1)
        self.assertEqual(datetime.fromtimestamp(task["due"]).date(), tomorrow)
        self.assertEqual(datetime.fromtimestamp(task["due"]).hour, 9)
        with patch("jarvis.routines.open_project") as launch:
            run_due(restored, root, task["due"] - 1)
            launch.assert_not_called()
            run_due(restored, root, task["due"])
            run_due(restored, root, task["due"] + 1)
            self.assertEqual(launch.call_count, 2)
            launch.assert_any_call(root, target=note)
        self.assertEqual(restored.execute("SELECT status FROM routines")[0]["status"], "concluída")
