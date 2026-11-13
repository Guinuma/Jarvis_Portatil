# Jarvis Portátil

Assistente de voz local no Windows com uma interface controlada por gestos da webcam.

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

Para arrancar pelo terminal, usa `python jarvis_holo.py` e abre [o painel local](http://localhost:4890). Abre uma pasta e uma nota com o rato e carrega em **Resumir com Qwen**. Com a webcam, agarra um cartão e comprime-o com as duas mãos para pedir o mesmo resumo.

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
