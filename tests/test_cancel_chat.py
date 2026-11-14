import http.client
import threading
import unittest
from contextlib import closing
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from unittest.mock import patch

from jarvis import app


class CancelChatTest(unittest.TestCase):
    def test_disconnect_closes_idle_upstream(self):
        closed = threading.Event()

        class Upstream(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.end_headers()
                self.connection.settimeout(4)
                try:
                    if self.connection.recv(1) == b"":
                        closed.set()
                except (TimeoutError, ConnectionError):
                    pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Upstream) as upstream, ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(app.Handler, key="test")
        ) as proxy:
            for server in (upstream, proxy):
                threading.Thread(target=server.serve_forever, daemon=True).start()
            real_open = app.urlopen

            def local_open(request, **kwargs):
                if request == app.OLLAMA_VERSION_URL:
                    return BytesIO(b"{}")
                return real_open(request, **kwargs)

            try:
                with patch.object(app, "HERMES_URL", f"http://127.0.0.1:{upstream.server_port}/"), patch.object(
                    app, "urlopen", local_open
                ), closing(http.client.HTTPConnection("127.0.0.1", proxy.server_port, timeout=5)) as client:
                    client.request("POST", "/chat", b'{"messages":[{"role":"user","content":"teste"}]}', {
                        "Content-Type": "application/json",
                        "Origin": f"http://127.0.0.1:{proxy.server_port}",
                    })
                    with client.getresponse() as response:
                        self.assertEqual(response.status, 200)
                self.assertTrue(closed.wait(3), "A ligação ao Hermes ficou aberta.")
            finally:
                proxy.shutdown()
                upstream.shutdown()
