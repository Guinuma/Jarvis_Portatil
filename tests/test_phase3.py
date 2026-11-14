import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from jarvis.memory import Memory
from jarvis.routines import run_due, schedule_programming, tomorrow_at_nine


class Phase3Test(unittest.TestCase):
    def test_memory_edit_delete_and_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Memory(directory, "first")
            self.assertIn("guardada", first.command("Lembra-te de que o meu projeto principal é o JARVIS."))
            record = first.list()[0]
            self.assertEqual(record["source"], "Conversa")
            self.assertEqual(record["value"], "JARVIS")
            self.assertTrue(record["updated"])
            self.assertEqual(Memory(directory, "second").list(), [])
            first.save(record["name"], "projeto", "JARVIS Portátil", "Editor")
            reopened = Memory(directory, "first")
            self.assertIn("JARVIS Portátil", reopened.command("Consulta a memória projeto principal"))
            reopened.command("Esquece isto projeto principal")
            self.assertEqual(first.list(), [])

    def test_scheduled_run_survives_reopen_and_executes_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            notes = root / "notes/2026-11-14"
            notes.mkdir(parents=True)
            (notes / "sessao.md").touch()
            when = tomorrow_at_nine(datetime(2026, 11, 14, 18))
            self.assertEqual(when, datetime(2026, 11, 15, 9))
            schedule_programming(Memory(directory, "test"), when)
            reopened = Memory(directory, "test")
            with patch("jarvis.routines.open_project") as launch:
                run_due(reopened, root, when.timestamp() - 1)
                launch.assert_not_called()
                run_due(reopened, root, when.timestamp())
                run_due(reopened, root, when.timestamp() + 1)
                launch.assert_called_once_with(root, files=[notes / "sessao.md"])
            entry = reopened.execute("SELECT * FROM routines")[0]
            self.assertEqual(entry["status"], "concluída")
            self.assertEqual(json.loads(entry["result"])["notas"], ["notes/2026-11-14/sessao.md"])

    def test_shopping_list_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory, "test")
            memory.command("Adiciona pão à lista de compras")
            memory.command("Adiciona leite à lista de compras")
            memory.command("Marca como comprado leite na lista de compras")
            reopened = Memory(directory, "test")
            self.assertIn("Comprado: leite", reopened.command("Mostra a lista de compras"))
            reopened.command("Remove pão da lista de compras")
            self.assertNotIn("pão", memory.command("Mostra a lista de compras"))
