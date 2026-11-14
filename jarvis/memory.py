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
        match = re.fullmatch(r"(?:jarvis[, ]+)?(?:consulta|mostra) (?:a )?memória (.+)", text, re.I)
        if match:
            records = self.execute("SELECT * FROM memories WHERE name = ?", (match[1].strip().casefold(),))
            if records:
                record = records[0]
                return f"Memória guardada ({record['source']}, {record['updated'][:10]}): {record['value']}"
            return "Não encontrei uma memória com esse nome."
        return None
