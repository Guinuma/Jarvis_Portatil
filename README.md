# Jarvis Portátil

Assistente de voz local no Windows com uma interface controlada por gestos da webcam.

Vê o [checklist de desenvolvimento](checklist.md) para acompanhar as cinco fases do projeto.

## Estrutura do repositório

- `jarvis/` contém a aplicação normal e o servidor do painel de gestos.
- `jarvis/ui/` contém a interface de chat e o código que liga as notas do H.O.L.O ao Ollama.
- `jarvis/integrations/` contém a ferramenta MCP de listagem de ficheiros.
- `scripts/` contém o diagnóstico, a comparação de modelos e o teste de aceitação da Fase 1. Executa os comandos com `python -m` a partir da raiz do repositório.
- `tests/` contém os testes automatizados. Corre `python -m unittest discover -v`.
- `holo/` é o submódulo H.O.L.O Hands.

Os dois atalhos Windows estão na raiz. O ficheiro `jarvis_files_mcp.py` na raiz mantém o caminho usado pelas instalações do Hermes já configuradas.

## Abrir a aplicação JARVIS

No Windows, abre **Iniciar Jarvis Normal.cmd** (ou executa `python -m jarvis.app --open`). O chat abre no navegador em `http://127.0.0.1:4889`. Com o gateway do Hermes local a correr, escreve «Que ficheiros tenho na pasta autorizada?». A atividade mostra as chamadas de ferramentas emitidas pelo Hermes durante o pedido.

Carrega em **Ditar** ou prime **Alt+Shift+D** com a janela do JARVIS em foco para iniciar ou parar o ditado. Podes usar o reconhecimento local em português de Portugal, se o navegador tiver suporte e o pacote de idioma estiver disponível. Revê a transcrição antes de carregar em **Enviar**. Para ouvir uma resposta, carrega em **Ouvir resposta**. A leitura usa uma voz portuguesa instalada no Windows e pode ser interrompida em **Parar leitura**. Ativa **Ler respostas automaticamente** para ouvir as frases à medida que chegam. A leitura automática começa desativada.

O servidor local lê a chave da API do Hermes a partir de `JARVIS_HERMES_API_KEY` ou do ficheiro `.env` do Hermes (em `%LOCALAPPDATA%\hermes` por predefinição). O botão **H.O.L.O Hands** inicia e abre o painel de gestos se o submódulo estiver instalado. O atalho **Iniciar Jarvis.cmd** continua a abrir diretamente esse painel.

## Verificar a base local

Com o Ollama aberto, corre `python -m scripts.check_local --ollama-only`. O diagnóstico confirma que o Ollama está a responder e que o modelo instalado anuncia suporte a ferramentas. O modelo predefinido é `qwen3:8b`. Para verificar outro modelo instalado, passa `--model nome:versão`. O Hermes 3 é uma opção de modelo a avaliar.

Para testar também o Hermes Agent, configura-o para usar o mesmo modelo no Ollama em `http://127.0.0.1:11434/v1`. Ativa a API do Hermes em `127.0.0.1:8642`, define a chave `API_SERVER_KEY` na configuração do Hermes e arranca com `hermes gateway`. Na sessão do PowerShell onde vais correr o diagnóstico, define `JARVIS_HERMES_API_KEY` com a mesma chave e corre `python -m scripts.check_local`.

O teste envia uma pergunta curta em português e verifica a hora na resposta. Depois de configurar a ferramenta de leitura, corre `python -m scripts.check_local --check-files` para confirmar que o Hermes emite um evento de conclusão para a listagem. O diagnóstico também pode ler a chave do ficheiro local do Hermes. A opção `--model` só verifica o modelo no Ollama. A escolha do modelo usado pelo agente é feita na configuração do Hermes. A execução efetiva de ferramentas ainda faz parte da base técnica em desenvolvimento.

[Configuração do Ollama no Hermes Agent](https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup) · [API local do Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)

### Testar a ferramenta de leitura

Para disponibilizar apenas a ferramenta de listagem à API local do Hermes, acrescenta ao `config.yaml` do Hermes as entradas abaixo. Se as secções já existirem, acrescenta as chaves às secções correspondentes. Usa o caminho absoluto do Python, do script e da pasta autorizada. No Windows, podes usar barras normais nos caminhos.

```yaml
mcp_servers:
  jarvis_files:
    command: C:/caminho/python.exe
    args:
      - C:/caminho/Jarvis_Portatil/jarvis/integrations/files_mcp.py
      - C:/caminho/Jarvis_Portatil/holo/sample-notes
platform_toolsets:
  api_server: [jarvis_files]
```

Reinicia o gateway e pede «Que ficheiros tenho na pasta autorizada?». A ferramenta devolve os nomes dos ficheiros na pasta indicada. Testa a recusa com «Usa listar_ficheiros com pasta ..». A ferramenta verifica o caminho resolvido e recusa pastas fora da raiz configurada.

Para verificar a Fase 1 de ponta a ponta, configura também os argumentos `--policy caminho/permissoes.json` e `--audit caminho/auditoria.jsonl` no servidor MCP. O JSON de permissões mapeia o nome da conta local que executa o gateway para as ferramentas autorizadas, por exemplo `{"conta-windows":["listar_ficheiros"]}`. A política é relida a cada chamada. A API do Hermes serve uma única conta local nesta fase. Usa as notas de exemplo como raiz e um ficheiro de auditoria fora da raiz.

Corre `python -m scripts.verify_phase1 --policy caminho/permissoes.json --audit caminho/auditoria.jsonl` sem outros pedidos em curso. O teste retira temporariamente a permissão, verifica a recusa e repõe a política no final. Para o teste de serviço parado, usa a opção `--offline` com o Ollama desligado e volta a abri-lo depois.


## Projetos de referência

- [Jarvis](https://github.com/isair/jarvis) para voz, chat e memória local com Ollama.
- [H.O.L.O Hands](https://github.com/zubair-trabzada/holo-gestures) para interagir com cartões e objetos 3D por gestos.

## Primeiro protótipo

Agarra um cartão de exemplo no H.O.L.O Hands e comprime-o com as duas mãos para pedir um resumo curto em português. O resumo aparece no painel. A pinça rápida abre a nota. O gesto de comprimir já pede um resumo no H.O.L.O e será reutilizado.

## Testar o protótipo no Windows

Com o Python instalado e o Ollama aberto, faz duplo clique em **Iniciar Jarvis.cmd**. O painel abre no navegador predefinido. Mantém a janela do Jarvis aberta enquanto usas o painel e prime **Ctrl+C** nessa janela para terminar.

Se for a primeira vez numa cópia do repositório, prepara o H.O.L.O e o modelo com estes comandos na pasta do projeto:

```powershell
git submodule update --init
ollama pull qwen3:8b
```

Para arrancar pelo terminal, usa `python -m jarvis.holo` e abre [o painel local](http://localhost:4890). Abre uma pasta e uma nota com o rato e carrega em **Resumir com Qwen**. Com a webcam, agarra um cartão e comprime-o com as duas mãos para pedir o mesmo resumo.

O servidor usa o Ollama na própria máquina. Para usar outro modelo instalado, define `$env:JARVIS_MODEL` antes de arrancar. Quando o resumo aparecer no painel, carrega em **Ouvir resumo**. A reprodução usa uma voz local em português do navegador, com preferência por português de Portugal. Se o botão indicar que falta uma voz, adiciona uma voz portuguesa nas definições de Voz do Windows e volta a abrir o navegador. A ligação ao Jarvis de desktop faz parte da etapa seguinte.

Para perguntar sobre um cartão, abre a nota, escreve no campo **Pergunta sobre esta nota** e carrega em **Perguntar**. O Qwen usa o conteúdo desse cartão para responder no leitor. Carrega em **Ouvir resposta** para ler o resultado com a mesma voz local usada nos resumos.

Para usar o microfone, carrega em **Ditar pergunta**, permite o acesso ao microfone e revê a transcrição antes de enviar. É preciso um navegador com reconhecimento no dispositivo e um pacote de português compatível. O primeiro uso pode descarregar esse pacote. Se o ditado local estiver indisponível, escreve a pergunta.

## Roadmap

| Etapa | Resultado esperado |
| --- | --- |
| 1. Validar a base | H.O.L.O com webcam, Jarvis com microfone e Ollama a responder no Windows. |
| 2. Ligar o gesto ao modelo | Uma nota de exemplo gera um resumo em português que aparece no painel. |
| 3. Integrar a voz | O resumo é lido em voz alta e o mesmo cartão pode dar contexto a uma pergunta por voz. |
| 4. Preparar a instalação | Uma pessoa consegue montar e testar o protótipo com as instruções do repositório. |

## Checklist

### 1. Validar a base

- [x] Verificar que Python e Ollama estão disponíveis no portátil.
- [x] Iniciar o servidor original do H.O.L.O e confirmar que a API devolve as duas notas de exemplo. Revisão testada: `55626ff`.
- [x] Pedir um resumo em português ao modelo local `qwen3:8b` pelo Ollama.
- [x] Correr o teste integrado em `?probe=1` no Edge (26/26) e abrir uma nota com o rato.
- [ ] Testar os gestos com a webcam física.
- [ ] Executar o Jarvis no Windows e confirmar entrada de microfone e saída de áudio em português.
- [ ] Inspecionar o fluxo de chat e voz do Jarvis para identificar por onde enviar contexto de um cartão e ler a resposta.

### 2. Ligar o gesto ao modelo

- [x] Fixar a revisão do H.O.L.O usada no protótipo e preservar a licença e os créditos.
- [x] Reutilizar a ação de resumo do H.O.L.O para enviar a nota selecionada a uma rota local.
- [x] Implementar o resumo no Ollama e a apresentação do resultado no painel.
- [x] Mostrar o estado de processamento e tratar pedidos repetidos, Ollama indisponível e modelo em falta.
- [x] Confirmar que a rota local resume uma nota de exemplo e trata uma nota vazia e um modelo em falta.
- [x] Confirmar no Edge que o botão gera e mostra um resumo de uma nota de exemplo.

### 3. Integrar a voz

- [x] Adicionar a reprodução pelo navegador e testar a seleção de voz local e a mensagem quando falta uma voz.
- [ ] Ouvir um resumo no portátil com uma voz portuguesa instalada.
- [x] Usar a nota aberta como contexto de uma pergunta escrita e confirmar a resposta no Edge.
- [x] Adicionar ditado local ao campo de pergunta e testar transcrição e cancelamento com reconhecimento simulado.
- [ ] Confirmar ditado em português com o microfone físico e um pacote local instalado.
- [ ] Validar a sequência completa com uma nota de exemplo, incluindo a troca de cartão entre pedidos.

### 4. Preparar a instalação

- [ ] Documentar a configuração e o arranque no Windows, incluindo a instalação inicial dos modelos.
- [ ] Repetir o teste com a Internet desligada depois de descarregar as dependências.
- [ ] Registar os passos para resolver problemas de câmara, microfone ou Ollama.
