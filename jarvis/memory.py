"""Memórias locais por perfil, com escrita atómica."""
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

KINDS = {"preferência", "contacto", "projeto", "dispositivo", "rotina", "nota"}
PROFILE = re.compile(r"[a-zA-Z0-9_-]{1,40}")


class Memory:
    def __init__(self, directory, profile):
        if not PROFILE.fullmatch(profile):
            raise ValueError("Nome de perfil inválido.")
        self.path = Path(directory) / f"{profile}.sqlite3"

    def execute(self, query, parameters=()):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            connection.execute("""CREATE TABLE IF NOT EXISTS memories (
                name TEXT PRIMARY KEY, kind TEXT NOT NULL, value TEXT NOT NULL,
                updated TEXT NOT NULL, source TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY, due REAL NOT NULL, status TEXT NOT NULL,
                result TEXT, finished REAL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS shopping (
                name TEXT PRIMARY KEY, bought INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                starts REAL NOT NULL, ends REAL NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS event_alerts (
                event_id INTEGER PRIMARY KEY, lead INTEGER NOT NULL, sent INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, due TEXT NOT NULL, days INTEGER NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS file_rules (
                id INTEGER PRIMARY KEY, event_path TEXT NOT NULL, condition_path TEXT,
                status TEXT NOT NULL DEFAULT 'pendente', result TEXT
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS pdf_index (
                path TEXT NOT NULL, ocr INTEGER NOT NULL, stamp TEXT NOT NULL,
                pages TEXT NOT NULL, PRIMARY KEY(path, ocr)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS download_plans (
                id INTEGER PRIMARY KEY, root TEXT NOT NULL, files TEXT NOT NULL, claimed INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS settings (
                name TEXT PRIMARY KEY, value TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS personal_checklists (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, items TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY, step INTEGER NOT NULL, status TEXT NOT NULL,
                data TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0, claim TEXT, lease REAL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS code_proposals (
                id INTEGER PRIMARY KEY, root TEXT NOT NULL, path TEXT NOT NULL,
                old_text TEXT NOT NULL, new_text TEXT NOT NULL, before_hash TEXT NOT NULL,
                after_hash TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'a rever'
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS download_watches (
                id INTEGER PRIMARY KEY, root TEXT NOT NULL, name TEXT NOT NULL COLLATE NOCASE,
                baseline TEXT, observed TEXT, observed_at REAL, finished REAL,
                status TEXT NOT NULL DEFAULT 'pendente', announced INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE UNIQUE INDEX IF NOT EXISTS pending_download_watch
                ON download_watches(root, name) WHERE status='pendente'""")
            connection.execute("""CREATE TABLE IF NOT EXISTS home_inventory (
                name_key TEXT NOT NULL, place_key TEXT NOT NULL, name TEXT NOT NULL,
                place TEXT NOT NULL, units INTEGER NOT NULL, PRIMARY KEY(name_key, place_key)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY, trader TEXT NOT NULL, category TEXT NOT NULL,
                category_key TEXT NOT NULL, cents INTEGER NOT NULL, day TEXT NOT NULL,
                void INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY, root TEXT NOT NULL, path TEXT NOT NULL, trader TEXT NOT NULL,
                trader_key TEXT NOT NULL, day TEXT NOT NULL, UNIQUE(root, path)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS study_cards (
                topic_key TEXT NOT NULL, topic TEXT NOT NULL, question_key TEXT NOT NULL,
                question TEXT NOT NULL, answer TEXT NOT NULL, explanation TEXT NOT NULL, source TEXT,
                PRIMARY KEY(topic_key, question_key)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS study_quizzes (
                id INTEGER PRIMARY KEY, topic TEXT NOT NULL, cards TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS study_difficulties (
                topic_key TEXT PRIMARY KEY, topic TEXT NOT NULL, detail TEXT NOT NULL, updated TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS meeting_materials (
                event_id INTEGER PRIMARY KEY, notes TEXT NOT NULL DEFAULT '',
                documents TEXT NOT NULL DEFAULT '[]', transcript TEXT, followup TEXT NOT NULL DEFAULT ''
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS research_journal (
                id INTEGER PRIMARY KEY, question TEXT NOT NULL, details TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS imported_mail (
                id INTEGER PRIMARY KEY, account_id TEXT NOT NULL, identity TEXT NOT NULL, folder TEXT NOT NULL,
                generation INTEGER NOT NULL, uid INTEGER NOT NULL, body BLOB NOT NULL, subject TEXT NOT NULL,
                subject_key TEXT NOT NULL, contacts TEXT NOT NULL, search_body TEXT NOT NULL, dated TEXT, stamp REAL,
                sender TEXT NOT NULL, UNIQUE(account_id, identity, folder, generation, uid)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS mail_sends (
                workflow_id INTEGER PRIMARY KEY, revision INTEGER NOT NULL, account_id TEXT NOT NULL,
                identity TEXT NOT NULL, smtp_identity TEXT NOT NULL, message_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL, detail TEXT NOT NULL, sent_at TEXT
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS meeting_recordings (
                id TEXT PRIMARY KEY, event_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'a gravar',
                path TEXT, consented_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            connection.execute("""CREATE UNIQUE INDEX IF NOT EXISTS active_meeting_recording
                ON meeting_recordings(event_id) WHERE status IN ('a gravar','a fechar')""")
            connection.execute("""CREATE TABLE IF NOT EXISTS meeting_segments (
                recording_id TEXT NOT NULL, number INTEGER NOT NULL, offset INTEGER NOT NULL,
                digest TEXT NOT NULL, cues TEXT NOT NULL, PRIMARY KEY(recording_id, number)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS meeting_insights (
                event_id INTEGER NOT NULL, path TEXT NOT NULL, digest TEXT NOT NULL,
                scope TEXT NOT NULL, items TEXT NOT NULL, PRIMARY KEY(event_id, digest, scope)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS pantry (
                item_key TEXT NOT NULL, unit TEXT NOT NULL, name TEXT NOT NULL,
                quantity INTEGER NOT NULL, PRIMARY KEY(item_key, unit)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS meal_recipes (
                name_key TEXT PRIMARY KEY, recipe TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS meal_plans (
                id INTEGER PRIMARY KEY, plan TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS local_previews (
                id INTEGER PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL, data TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'a rever'
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS delete_reviews (
                id INTEGER PRIMARY KEY, path TEXT NOT NULL, token TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'a rever', detail TEXT
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS remote_drafts (
                workflow_id INTEGER NOT NULL, revision INTEGER NOT NULL, account_id TEXT NOT NULL,
                identity TEXT NOT NULL, folder TEXT NOT NULL, message_id TEXT NOT NULL UNIQUE, state TEXT NOT NULL,
                PRIMARY KEY(workflow_id, revision, account_id)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS matrix_outbox (
                id INTEGER PRIMARY KEY, room TEXT NOT NULL, fingerprint TEXT NOT NULL,
                transaction_id TEXT NOT NULL UNIQUE, message TEXT NOT NULL,
                state TEXT NOT NULL DEFAULT 'a rever', event_id TEXT
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS external_action_reviews (
                id INTEGER PRIMARY KEY, preview_id INTEGER NOT NULL, action TEXT NOT NULL, fingerprint TEXT NOT NULL,
                snapshot TEXT NOT NULL, payload TEXT NOT NULL, reference TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL DEFAULT 'a rever', UNIQUE(preview_id, action, payload)
            )""")
            return [dict(row) for row in connection.execute(query, parameters)]

    def list(self):
        return self.execute("SELECT * FROM memories ORDER BY name")

    def save(self, name, kind, value, source):
        if not isinstance(name, str) or not isinstance(value, str) or not name.strip() or not value.strip():
            raise ValueError("Preenche o nome e a informação da memória.")
        if kind not in KINDS or len(name) > 150 or len(value) > 4000:
            raise ValueError("Tipo ou tamanho de memória inválido.")
        self.execute("""INSERT INTO memories VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET kind=excluded.kind, value=excluded.value,
            updated=excluded.updated, source=excluded.source""",
            (name.strip().casefold(), kind, value.strip(), datetime.now().astimezone().isoformat(), source))

    def delete(self, name):
        self.execute("DELETE FROM memories WHERE name = ?", (name.strip().casefold(),))

    def command(self, text):
        if re.fullmatch(r"(?:mostra|consulta) (?:a )?lista de compras[.!]?", text, re.I):
            items = self.execute("SELECT * FROM shopping ORDER BY bought, name")
            return "\n".join(
                f'{"Comprado" if item["bought"] else "Por comprar"}: {item["name"]}'
                for item in items
            ) or "A lista de compras está vazia."
        shopping = re.fullmatch(
            r"(adiciona|remove|marca como comprado) (.+?) (?:à|da|na) lista de compras[.!]?", text, re.I
        )
        if shopping:
            action, name = shopping.groups()
            name = name.strip().casefold()
            if not name or len(name) > 150:
                raise ValueError("Indica um artigo com até 150 caracteres.")
            query = {
                "adiciona": "INSERT INTO shopping (name) VALUES (?) ON CONFLICT(name) DO NOTHING RETURNING name",
                "remove": "DELETE FROM shopping WHERE name = ? RETURNING name",
                "marca como comprado": "UPDATE shopping SET bought = 1 WHERE name = ? RETURNING name",
            }[action.casefold()]
            changed = self.execute(query, (name,))
            if not changed:
                return "A lista de compras ficou igual."
            return f"Lista de compras atualizada: {name}."
        match = re.fullmatch(r"(?:jarvis[, ]+)?lembra-te(?: de que| disto:?)?\s+(.+)", text, re.I)
        if match:
            note = match[1].strip()
            project = re.fullmatch(r"o meu projeto principal é (?:o )?(.+?)[.!]?", note, re.I)
            name, kind, value = ("projeto principal", "projeto", project[1]) if project else (note[:150], "nota", note)
            self.save(name, kind, value, "Conversa")
            return f"Memória guardada: {name}."
        match = re.fullmatch(r"(?:jarvis[, ]+)?esquece(?: isto:?)? (.+)", text, re.I)
        if match:
            self.delete(match[1])
            return "Memória removida."
        match = re.fullmatch(
            r"(?:jarvis[, ]+)?(?:consulta|mostra) (?:(?:a|o) )?"
            r"(memória|preferência|contacto|projeto|dispositivo|rotina) (.+)",
            text, re.I,
        )
        if match:
            kind = match[1].casefold()
            name = match[2].strip().rstrip(".!?").casefold()
            records = self.execute(
                "SELECT * FROM memories WHERE name = ? AND (? = 'memória' OR kind = ?)",
                (name, kind, kind),
            )
            if records:
                record = records[0]
                return f"Memória guardada ({record['source']}, {record['updated'][:10]}): {record['value']}"
            return "Não encontrei uma memória com esse nome."
        return None
