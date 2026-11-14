# Fase 2 — Guião de validação manual

A execução destes testes fica a cargo do utilizador. Todas as caixas estão por marcar.
Marca cada uma apenas quando observares o resultado indicado. Podes distribuir os testes por várias sessões.

## Antes de começar

- [ ] Arrancar o Ollama, o gateway do Hermes e **Iniciar Jarvis Normal.cmd**; abrir `http://127.0.0.1:4889` e atualizar a página para carregar a versão nova.
- [ ] Confirmar que o VS Code está instalado e que o Windows tem uma voz portuguesa, como **Microsoft Helia (pt-PT)**.
- [ ] Confirmar a instalação das dependências com `python -m pip install -r requirements.txt`, se estiveres a preparar outro computador.
- [ ] Preparar o modelo de ditado com `python -m scripts.setup_voice`, se ainda não existir nesse computador. Esta preparação requer Internet; a transcrição seguinte é local.
- [ ] Fazer os testes de ficheiros numa pasta de ensaio, sem documentos importantes. Guardar o volume e a saída de áudio atuais para os repor no fim.

O modelo Whisper `small` e a voz Helia já foram encontrados/preparados neste portátil durante o desenvolvimento. Não é necessário voltar a descarregar o modelo em cada utilização.

## 1. Chat, contexto e idioma

- [ ] Enviar «Olá, Jarvis» e confirmar que aparece uma resposta legível e que o estado volta a **Pronto**.
- [ ] Enviar «Nesta conversa a palavra de teste é girassol», seguido de «Qual é a palavra de teste?». Esperado: recuperar **girassol**.
- [ ] Pedir «Responde em inglês: explica um temporizador numa frase». Esperado: uma frase em inglês.
- [ ] Pedir «Agora em português de Portugal, explica com três exemplos». Esperado: resposta em português, com mais detalhe e três exemplos.
- [ ] Pedir «Mais curto». Esperado: reduzir a resposta anterior mantendo o assunto.
- [ ] Abrir **Nova conversa** e confirmar que o painel fica vazio; reabrir a anterior no histórico e confirmar que as mensagens reaparecem.
- [ ] Enviar um pedido longo e premir **Cancelar pedido**. Esperado: parar a apresentação da resposta e permitir enviar outro pedido.
- [ ] Enviar outro pedido depois do cancelamento e confirmar que a interface continua utilizável.

## 2. Microfone e ditado

No reconhecimento nativo compatível podem aparecer palavras durante a escuta. Na alternativa Whisper, o áudio é gravado e o texto aparece **depois de parar o ditado**. O limite é de 60 segundos por gravação. O texto deve ser revisto antes de enviar.

- [ ] Premir **Ditar**, autorizar o microfone e confirmar **Microfone ativo** e o indicador de captura do navegador.
- [ ] Dizer «Consulta a bateria», premir **Parar ditado** e confirmar que a captura termina e aparece a transcrição.
- [ ] Rever a transcrição, corrigir qualquer erro e premir **Enviar**. Esperado: apresentar a bateria reportada pelo Windows.
- [ ] Repetir com **Alt+Shift+D** para iniciar e parar, mantendo o JARVIS em foco.
- [ ] Selecionar outro microfone disponível e confirmar que a captura vem desse dispositivo.
- [ ] Recusar a permissão de microfone nas definições do navegador e tentar ditar. Esperado: mensagem compreensível, sem perder o rascunho e mantendo disponível a escrita.
- [ ] Voltar a autorizar o microfone e confirmar que o ditado pode ser retomado.
- [ ] Gravar silêncio e parar. Esperado: não executar ações nem enviar automaticamente uma mensagem.
- [ ] Deixar uma gravação atingir 60 segundos. Esperado: terminar a captura e transcrever o que foi gravado.
- [ ] Num navegador com reconhecimento nativo local, confirmar que a transcrição parcial aparece durante a escuta.
- [ ] Iniciar um pedido demorado, premir **Ditar**, dizer «cancela» e parar o ditado. Esperado: cancelar o pedido se ainda estiver em curso. No Whisper, o cancelamento só é reconhecido depois da transcrição.
- [ ] Premir **Escape** durante a escuta. Esperado: terminar a captura; o áudio já gravado pode ser transcrito para revisão, mas não é enviado automaticamente.

## 3. Leitura em voz alta

- [ ] Premir **Ouvir resposta** e confirmar que ouves a resposta nos altifalantes/auscultadores pretendidos.
- [ ] Confirmar que **Automática** escolhe uma voz PT-PT quando existe uma instalada.
- [ ] Selecionar uma voz diferente, se existir, e confirmar a alteração na leitura seguinte.
- [ ] Alternar entre **Lenta**, **Normal** e **Rápida** e confirmar a diferença no ritmo.
- [ ] Durante uma frase, premir **Parar leitura**. Esperado: interromper o áudio e não reproduzir frases que estavam em fila.
- [ ] Repetir a interrupção com **Escape**.
- [ ] Ativar **Ler respostas automaticamente** e pedir uma resposta com várias frases. Esperado: ouvir as frases recebidas pela aplicação.
- [ ] Parar a leitura automática enquanto o texto continua a chegar. Esperado: as frases seguintes desse pedido também não são lidas.
- [ ] Confirmar que a legenda acompanha o trecho lido e desaparece ao terminar ou interromper.
- [ ] Desativar a leitura automática e confirmar que uma nova resposta chega apenas por texto.
- [ ] Reabrir a aplicação e confirmar que voz, velocidade e leitura automática mantêm as definições guardadas.

## 4. Windows e aplicações

- [ ] Pedir «Abre a calculadora» e confirmar que abre a Calculadora.
- [ ] Repetir para «Abre o bloco de notas», «Abre o explorador» e «Abre o Paint».
- [ ] Pedir «Abre o site https://example.org» e confirmar a abertura no navegador predefinido.
- [ ] Pedir «Consulta o volume» e comparar com o nível mostrado no Windows.
- [ ] Pedir «Define o volume para 25%» e confirmar no Windows; repor o volume anterior no fim.
- [ ] Pedir «Define o volume para 150%». Esperado: recusa com indicação do intervalo permitido, sem alteração de volume.
- [ ] Pedir «Mostra as saídas de áudio» e confirmar que apresenta as saídas ativas.
- [ ] Pedir «Muda a saída de áudio para NOME», substituindo NOME pelo nome exato apresentado. Se houver nomes repetidos, usar o identificador completo. Confirmar a seleção no Windows.
- [ ] Ler uma resposta e confirmar que o som sai no dispositivo escolhido; repor a saída anterior.
- [ ] Premir **Saída de áudio do Windows** e confirmar que abre as definições de som.

## 5. Projetos, pesquisa e referências

Para outros projetos, configurar `JARVIS_PROJECTS_FILE` conforme o README e reiniciar o servidor. Usar duas pastas de ensaio com o mesmo nome lógico para testar ambiguidades.

- [ ] Pedir «Jarvis, abre o meu projeto no VS Code». Esperado: abrir a pasta do JARVIS no editor.
- [ ] Pedir «Abre o projeto NOME no VS Code» para outro projeto autorizado. Esperado: abrir a pasta configurada.
- [ ] Pedir um nome de projeto que corresponda a duas pastas. Esperado: mostrar ambas e aguardar a seleção, sem abrir nenhuma.
- [ ] Responder «opção 2» e confirmar que abre a segunda pasta apresentada.
- [ ] Pedir uma pasta não autorizada. Esperado: recusar a abertura.
- [ ] Num ambiente sem VS Code disponível, repetir a abertura. Esperado: explicar que o editor está indisponível.
- [ ] Criar manualmente `teste-fase2-a.txt` e `teste-fase2-b.txt` na pasta de ensaio, ambos com a frase «marcador de pesquisa».
- [ ] Pedir «Encontra o ficheiro teste-fase2» no projeto JARVIS. Esperado: encontrar os nomes correspondentes e mostrar os pedidos de abertura.
- [ ] Pedir «Procura conteúdo marcador de pesquisa». Esperado: encontrar os ficheiros que contêm a frase.
- [ ] Pedir `Encontra o ficheiro teste-fase2 no projeto "NOME"` e `Procura conteúdo marcador de pesquisa no projeto "NOME"`. Esperado: procurar no outro projeto autorizado e identificar esse projeto nos pedidos de abertura.
- [ ] Depois de uma pesquisa com um único resultado, pedir «Abre esse ficheiro». Esperado: abrir o ficheiro encontrado.
- [ ] Depois de uma pesquisa com dois resultados, pedir «Abre esse ficheiro». Esperado: pedir seleção, sem escolher sozinho.
- [ ] Responder «opção 1» e confirmar a abertura do primeiro resultado.
- [ ] Repetir uma escolha ambígua e responder «cancela». Esperado: não executar nenhuma abertura; uma seleção posterior sem novas opções não deve reutilizar a escolha cancelada.
- [ ] Tentar abrir `../fora.txt`. Esperado: recusar o caminho exterior à pasta autorizada.
- [ ] Criar uma nota numa pasta `notes/AAAA-MM-DD/` e pedir «Encontra as notas da última sessão». Esperado: mostrar a data mais recente com notas e os caminhos corretos.
- [ ] Repetir «Encontra as notas da última sessão do projeto NOME» para outro projeto autorizado.

## 6. Criação de ficheiros e notas

- [ ] Pedir «Cria o ficheiro ensaio-fase2.txt». Esperado: criar um ficheiro vazio na pasta do projeto e indicar a localização.
- [ ] Escrever conteúdo nesse ficheiro e repetir o pedido de criação. Esperado: recusar a sobrescrita e preservar o conteúdo.
- [ ] Pedir «Guarda uma nota Rever os resultados da fase dois». Esperado: criar uma nota na pasta da data atual com esse texto.
- [ ] Abrir a nota e confirmar o conteúdo.

## 7. Agenda

A agenda implementada é **local ao perfil JARVIS**. Não inclui automaticamente os eventos do Google Calendar ou Outlook. Não interpretar «livre» como disponibilidade nesses serviços. Nas instruções seguintes, substituir `AAAA-MM-DD` por uma data de ensaio.

- [ ] Pedir `Cria um evento "Ensaio A" em AAAA-MM-DD 10:00 por 60 minutos`.
- [ ] Pedir `Consulta agenda AAAA-MM-DD`. Esperado: mostrar Ensaio A às 10:00 e o número do evento.
- [ ] Pedir `Consulta disponibilidade AAAA-MM-DD 09:00 até 12:00`. Se não houver outros eventos, esperar os intervalos 09:00–10:00 e 11:00–12:00.
- [ ] Consultar um intervalo totalmente ocupado. Esperado: informar que não há períodos livres.
- [ ] Pedir um intervalo com o fim anterior ao início. Esperado: recusar e explicar o problema.
- [ ] Criar um único evento para amanhã e perguntar «A que horas é a reunião de amanhã?». Esperado: indicar o compromisso e a hora da agenda local.
- [ ] Criar outro evento para amanhã e repetir. Esperado: mostrar os compromissos e pedir para identificar o evento.
- [ ] Pedir «Mostra o evento N», com o número escolhido. Esperado: mostrar título, data e horário desse evento.

## 8. Temporizadores e lembretes

Estes lembretes são mantidos pelo separador aberto. Fechar ou recarregar a página perde os temporizadores desta versão; não os confundir com as rotinas persistentes da Fase 3. O computador em suspensão pode atrasar o aviso.

- [ ] Pedir «Cria um temporizador de 10 segundos». Esperado: um único aviso após esse intervalo.
- [ ] Pedir «Lembra-me daqui a 20 segundos de beber água». Esperado: comunicar a hora e emitir um único aviso.
- [ ] Antes do disparo, pedir «afinal, daqui a 30 segundos». Esperado: substituir o horário e não emitir o aviso antigo.
- [ ] Criar outro lembrete e pedir «Cancela o último lembrete». Esperado: não emitir esse aviso.
- [ ] Pedir cancelamento sem lembrete pendente. Esperado: informar que não existe um lembrete para cancelar.
- [ ] Pedir «Lembra-me às HH:MM de fazer uma pausa», escolhendo uma hora próxima. Esperado: comunicar a próxima ocorrência dessa hora.
- [ ] Pedir «Lembra-me daqui a quarenta e cinco minutos de fazer uma pausa». Esperado: interpretar 45 minutos; cancelar depois se não quiseres esperar.
- [ ] Premir **Enviar** repetidamente durante o processamento. Esperado: não criar cópias do mesmo pedido enquanto o botão está desativado.

## 9. Painel, teclado e acessibilidade

- [ ] Usar **Tab** e **Shift+Tab** para percorrer os controlos. Esperado: foco visível e ordem compreensível, sem ficar preso.
- [ ] Escrever e enviar com **Enter**, iniciar/parar ditado com **Alt+Shift+D** e interromper leitura/pedido com **Escape**.
- [ ] Com o Narrador do Windows, confirmar os nomes dos botões e campos e os anúncios de estado do microfone, transcrição, resposta e erros.
- [ ] Confirmar que texto, controlos, foco e mensagens se distinguem do fundo, incluindo com zoom a 200%.
- [ ] Pedir «Que ficheiros tenho na pasta de teste?» com o Hermes e a ferramenta MCP configurados. Esperado: mostrar início e conclusão da ferramenta no painel de atividade.
- [ ] Premir **H.O.L.O Hands**. Esperado: abrir o painel quando o submódulo está instalado; caso contrário, mostrar uma mensagem útil.

## 10. Falhas e funcionamento sem Internet

- [ ] Com os componentes já instalados, desligar a Internet e pedir uma resposta de conversa ao modelo local.
- [ ] Ainda sem Internet, ditar uma frase, rever o texto, enviar um comando local e ouvir uma resposta.
- [ ] Sem Internet, abrir a Calculadora e consultar a bateria. Esperado: continuarem disponíveis.
- [ ] Parar o gateway do Hermes e enviar uma pergunta de conversa. Esperado: identificar a indisponibilidade, sem bloquear permanentemente o chat.
- [ ] Com o Hermes parado, consultar a agenda local ou criar um temporizador. Esperado: continuar a funcionar.
- [ ] Voltar a arrancar o Hermes e confirmar que a conversa recupera.
- [ ] Parar o Ollama e pedir uma resposta de conversa. Esperado: indicar que o Ollama não respondeu; voltar a arrancá-lo depois.
- [ ] Repor a Internet e as definições de som anteriores no fim.

## 11. Aceitação completa — 45 minutos

Este ensaio fica exclusivamente a cargo do utilizador. O ensaio automático iniciado anteriormente foi interrompido e **não validou o disparo aos 45 minutos**.

> Jarvis, abre o meu projeto, encontra as notas da última sessão e lembra-me daqui a 45 minutos de fazer uma pausa.

- [ ] Dizer a frase pelo microfone e parar o ditado.
- [ ] Confirmar que a transcrição preserva as três ações e **45 minutos**. Anotar os erros de reconhecimento antes de os corrigir.
- [ ] Rever o texto e enviar uma única vez; anotar a hora do envio e a hora comunicada para o aviso.
- [ ] Confirmar no VS Code que abriu o projeto correto.
- [ ] Confirmar que os caminhos apresentados pertencem às notas da última sessão.
- [ ] Confirmar que a hora comunicada corresponde ao envio mais 45 minutos.
- [ ] Manter o separador aberto e o computador acordado durante os 45 minutos.
- [ ] Confirmar que o aviso de pausa aparece uma única vez; se a leitura automática estiver ativa, confirmar também o áudio.
- [ ] Esperar mais um minuto e confirmar que o aviso não se repete.

## Limitações conhecidas e resultados a registar

- A transcrição pode trocar palavras. Num ensaio anterior com áudio sintetizado, introduziu erros em «Jarvis» e no intervalo; o comando não foi executado sem correção. A revisão do texto é obrigatória no fluxo atual.
- O Whisper não fornece transcrição parcial neste fluxo; o reconhecimento nativo compatível pode fornecê-la.
- A primeira resposta do modelo de conversa pode demorar mais enquanto carrega. Anotar separadamente a demora da primeira pergunta e das seguintes.
- Não existe ligação automática a calendários externos nesta implementação.
- Os testes já executados durante o desenvolvimento não substituem esta validação manual. Não foram executados novos testes após o pedido para os deixar a cargo do utilizador.

Para reportar um problema, copiar este bloco e preencher:

```text
Teste / secção:
Data e hora:
Navegador:
Pedido exato:
Transcrição apresentada (se aplicável):
Resultado esperado:
Resultado observado / mensagem de erro:
O problema repete-se?:
```
