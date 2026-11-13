# Jarvis Portátil

Assistente de voz local no Windows com uma interface controlada por gestos da webcam.

## Projetos de referência

- [Jarvis](https://github.com/isair/jarvis) para voz, chat e memória local com Ollama.
- [H.O.L.O Hands](https://github.com/zubair-trabzada/holo-gestures) para interagir com cartões e objetos 3D por gestos.

## Primeiro protótipo

Abre uma nota de exemplo no H.O.L.O Hands e comprime o cartão com as duas mãos. A integração deve enviar o texto ao modelo local e mostrar e ler um resumo curto em português. A pinça rápida abre a nota. O gesto de comprimir já pede um resumo no H.O.L.O e será reutilizado.

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
- [ ] Abrir o H.O.L.O no navegador, correr o teste integrado em `?probe=1` e testar com webcam e rato.
- [ ] Executar o Jarvis no Windows e confirmar entrada de microfone e saída de áudio em português.
- [ ] Inspecionar o fluxo de chat e voz do Jarvis para identificar por onde enviar contexto de um cartão e ler a resposta.

### 2. Ligar o gesto ao modelo

- [ ] Fixar a revisão do H.O.L.O usada no protótipo e preservar a licença e os créditos.
- [ ] Reutilizar a ação de resumo do H.O.L.O para enviar a nota selecionada a uma rota local.
- [ ] Gerar um resumo curto em português no Ollama e mostrá-lo no painel.
- [ ] Mostrar o estado de processamento e tratar pedidos repetidos, Ollama indisponível e modelo em falta.
- [ ] Confirmar que o pedido funciona com o gesto e que há uma ação equivalente com o rato.

### 3. Integrar a voz

- [ ] Ligar a resposta à voz local e verificar a reprodução de um resumo em português.
- [ ] Passar a nota selecionada como contexto para uma pergunta por voz, como “Qual é o prazo desta nota?”.
- [ ] Validar a sequência completa com uma nota de exemplo, incluindo a troca de cartão entre pedidos.

### 4. Preparar a instalação

- [ ] Documentar a configuração e o arranque no Windows, incluindo a instalação inicial dos modelos.
- [ ] Repetir o teste com a Internet desligada depois de descarregar as dependências.
- [ ] Registar os passos para resolver problemas de câmera, microfone ou Ollama.
