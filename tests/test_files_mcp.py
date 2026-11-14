"""Regressões do registo e da execução da ferramenta MCP."""
import json
import tempfile
import unittest
from pathlib import Path

from jarvis.integrations.files_mcp import respond


class FileToolTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve() / "autorizada"
        self.root.mkdir()
        (self.root / "notas.md").touch()
        (self.root.parent / "privado.md").touch()

    def call(self, arguments):
        return respond({"id": 1, "method": "tools/call", "params": {
            "name": "listar_ficheiros", "arguments": arguments,
        }}, self.root)["result"]

    def test_registo_publica_argumento_e_leitura(self):
        result = respond({"id": 1, "method": "tools/list"}, self.root)
        self.assertEqual(len(result["result"]["tools"]), 1)
        tool = result["result"]["tools"][0]
        self.assertEqual(tool["name"], "listar_ficheiros")
        self.assertEqual(tool["inputSchema"]["required"], ["pasta"])
        self.assertTrue(tool["annotations"]["readOnlyHint"])

    def test_lista_a_pasta_autorizada(self):
        result = self.call({"pasta": "."})
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"]), {"ficheiros": ["notas.md"]})

    def test_recusa_argumentos_invalidos(self):
        for arguments in ({}, {"pasta": 12}, {"pasta": ""}, {"pasta": ".", "outro": 1},
                          {"pasta": str(self.root)}):
            with self.subTest(arguments=arguments):
                self.assertTrue(self.call(arguments)["isError"])

    def test_recusa_pasta_externa_e_pasta_inexistente(self):
        for folder in ("..", "não-existe"):
            with self.subTest(folder=folder):
                result = self.call({"pasta": folder})
                self.assertTrue(result["isError"])
                self.assertNotIn("privado.md", result["content"][0]["text"])

    def test_recusa_sem_autorizacao_antes_da_listagem(self):
        from unittest.mock import patch

        policy = self.root.parent / "policy.json"
        policy.write_text(json.dumps({"alice": ["listar_ficheiros"]}), encoding="utf-8")
        request = {"id": 1, "method": "tools/call", "params": {
            "name": "listar_ficheiros", "arguments": {"pasta": "."},
        }}
        self.assertFalse(respond(request, self.root, user="alice", policy=policy)["result"]["isError"])
        with patch("jarvis.integrations.files_mcp.list_files") as read:
            self.assertTrue(respond(request, self.root, user="bob", policy=policy)["result"]["isError"])
            read.assert_not_called()
