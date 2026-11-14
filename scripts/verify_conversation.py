"""Teste real do contexto, idioma e detalhe através do Hermes e Ollama."""
import json
import os
import tempfile
import threading
import time
import uuid
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from jarvis.app import Handler, api_key


def main():
    with tempfile.TemporaryDirectory() as directory:
        os.environ['JARVIS_DATA_DIR'] = directory
        with ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, key=api_key())) as server:
            worker = threading.Thread(target=server.serve_forever)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
            session = str(uuid.uuid4())
            history = []
            prompts = [
                'Nesta conversa, a palavra de teste é girassol. Responde apenas «Entendido».',
                'Qual é a palavra de teste que te dei? Responde só com a palavra.',
                'From now on answer in English. Explain what a timer does in one short sentence.',
                'Agora responde em português de Portugal, com mais detalhe: explica os temporizadores em três pontos, com um exemplo em cada um.',
            ]
            try:
                for index, prompt in enumerate(prompts):
                    history.append({'role':'user', 'content':prompt})
                    request = Request(base+'/chat', json.dumps({'session_id':session, 'messages':history}).encode(),
                                      {'Content-Type':'application/json', 'Origin':base})
                    started = time.monotonic()
                    answer, complete = '', False
                    with urlopen(request, timeout=300) as response:
                        for line in response:
                            if not line.startswith(b'data:'):
                                continue
                            value = line[5:].strip()
                            if value == b'[DONE]':
                                complete = True
                                break
                            data = json.loads(value)
                            for choice in data.get('choices', []):
                                answer += choice.get('delta', {}).get('content') or ''
                    assert complete and answer.strip(), answer
                    if index == 1:
                        assert 'girassol' in answer.casefold(), answer
                    if index == 2:
                        assert 'timer' in answer.casefold() and len(answer.split()) <= 55, answer
                    if index == 3:
                        assert 'temporizador' in answer.casefold() and len(answer.split()) > 55, answer
                    history.append({'role':'assistant','content':answer})
                    print(json.dumps({'step':index+1, 'seconds':round(time.monotonic()-started,2), 'answer':answer},ensure_ascii=False),flush=True)
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    main()
