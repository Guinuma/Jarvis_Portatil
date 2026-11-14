import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from jarvis.agenda import agenda_command
from jarvis.conversation import resolve_reference
from jarvis.integrations.project_files import file_command
from jarvis.memory import Memory


class Phase2Test(unittest.TestCase):
    def test_spoken_reminder_numbers(self):
        import time
        from jarvis.integrations.reminders import parse_reminder, COMBINED
        from jarvis.integrations.editor import normalize
        for quantity in ['45', 'quarenta e cinco', '40 e 5']:
            label, due = parse_reminder(f'Lembra-me daqui a {quantity} minutos de pausa')
            self.assertEqual(label, 'pausa')
            self.assertAlmostEqual(due - time.time(), 2700, delta=1)
        self.assertIsNotNone(COMBINED.match(normalize('Jarvis, abre o meu projeto. Encontre as notas da última sessão e lembra-me daqui a 45 minutos de pausa.')))
        with self.assertRaises(ValueError):
            parse_reminder('Lembra-me daqui a zero minutos de pausa')

    def test_search_scoped_project_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            other = root / 'other'
            other.mkdir()
            (other / 'sessao.md').write_text('Temporizadores portugueses', encoding='utf-8')
            config = root / 'projects.json'
            config.write_text(json.dumps([{'nome':'Outro', 'pasta':str(other)}]), encoding='utf-8')
            with patch.dict(os.environ, {'JARVIS_PROJECTS_FILE': str(config)}):
                for query in ['Encontra ficheiro sessao', 'Procura conteúdo Temporizadores']:
                    reply = file_command(query + ' no projeto "Outro"', root)
                    self.assertIn('sessao.md', reply)
                    self.assertIn(str(other), reply)
                with self.assertRaisesRegex(ValueError, 'autorizado'):
                    file_command('Encontra ficheiro sessao no projeto "Proibido"', root)
                with self.assertRaises(ValueError):
                    file_command('Abre ficheiro "../projects.json" no projeto "Outro"', root)

    def test_free_slots_and_tomorrow_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(directory, 'test')
            day = date.today() + timedelta(days=1)
            agenda_command(f'Cria um evento "Reunião" em {day} 10:00 por 60 minutos', memory)
            slots = agenda_command(f'Consulta disponibilidade {day} 09:00 até 12:00', memory)
            self.assertIn('09:00–10:00', slots)
            self.assertIn('11:00–12:00', slots)
            self.assertNotIn('10:00–11:00', slots)
            messages = [{'role':'user', 'content':'A que horas é a reunião de amanhã?'}]
            self.assertIn('Reunião · 10:00', resolve_reference(messages, memory)[1])
            agenda_command(f'Cria um evento "Outra" em {day} 11:00 por 30 minutos', memory)
            self.assertIn('vários compromissos', resolve_reference(messages, memory)[1])
            with self.assertRaises(ValueError):
                agenda_command(f'Consulta disponibilidade {day} 12:00 até 09:00', memory)

    def test_reference_requires_selection_and_revalidates_path(self):
        messages = [{'role':'assistant', 'content':'Ficheiros encontrados:\nAbre o ficheiro "a.md"\nAbre o ficheiro "b.md"'},
                    {'role':'user', 'content':'Abre esse ficheiro'}]
        text, reply = resolve_reference(messages, None)
        self.assertIn('vários ficheiros', reply)
        messages.extend([{'role':'assistant', 'content':reply}, {'role':'user','content':'opção 2'}])
        self.assertEqual(resolve_reference(messages, None), ('Abre o ficheiro "b.md"', None))
        messages[0]['content'] = 'Abre o ficheiro "a.md"'
        self.assertEqual(resolve_reference(messages[:2], None), ('Abre o ficheiro "a.md"', None))

    def test_voice_rejects_empty_or_missing_model(self):
        from jarvis.integrations.voice import transcribe
        with self.assertRaises(ValueError):
            transcribe(b'')
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'JARVIS_WHISPER_MODEL':directory}):
            with self.assertRaisesRegex(ValueError, 'Prepara'):
                transcribe(b'audio')
