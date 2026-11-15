# JARVIS Portátil — Checklist de testes

Marca com **[x]** os ensaios executados com o resultado esperado. As marcações históricas conservam o âmbito registado, como simulação ou validação de desenvolvimento. Os testes em aberto ficam para a validação da aplicação completa.

Para o estado das funcionalidades, consulta o [checklist de implementação](../checklist.md).

## Fase 1 — Base técnica

### Funcionamento local e desempenho

- [x] Enviar um pedido de teste ao Ollama no portátil e confirmar que responde.
- [x] Enviar um pedido na aplicação JARVIS e confirmar que chega ao modelo através do Hermes.
- [x] Confirmar uma chamada real à ferramenta de listagem com `qwen3:8b`.
- [x] Comparar os candidatos, incluindo Hermes 3, no mesmo portátil quanto à compreensão de português de Portugal, à escolha da ferramenta e ao tempo de resposta.
- [x] Confirmar que o modelo devolve o nome da ferramenta e argumentos válidos, e que o Hermes Agent usa o resultado da execução para responder.
- [x] Testar pedidos em português de Portugal com datas, horas e expressões como «daqui a 45 minutos» e «a reunião de amanhã».
- [x] Medir o tempo até ao início da resposta, o consumo de memória e a taxa de sucesso das chamadas de ferramentas num conjunto fixo de pedidos.

### Comparação no portátil

Executar `python -m scripts.compare_models qwen3:8b hermes3:3b` com ambos os modelos instalados. Os quatro pedidos usam o Ollama diretamente. As ferramentas de listagem e agenda são apenas esquemas para testar a seleção e os argumentos. A execução real da listagem pelo Hermes Agent foi verificada separadamente.

| Modelo | Hora e data | Chamadas com argumentos corretos | Primeiro texto ou chamada | Memória do modelo no Ollama |
| --- | --- | --- | --- | --- |
| `qwen3:8b` | 2/2 | 1/2 | 1,12–9,78 s | 5,95 GB |
| `hermes3:3b` | 1/2 | 0/2 | 0,40–3,10 s nos três pedidos com saída | 2,57 GB |

Mantém-se o `qwen3:8b` no Hermes Agent. No teste direto, acertou na hora e na data de amanhã, mas usou `autorizada` como caminho em vez de `.` na listagem. O Hermes 3 anunciou suporte a ferramentas, mas não devolveu chamadas estruturadas válidas neste teste. A amostra consiste numa passagem por modelo. Os tempos incluem o estado de carregamento de cada pedido nessa passagem.

### Extensões e manutenção

- [x] Confirmar pela API local que o Hermes chama a ferramenta de listagem MCP e usa o resultado.
- [x] Validar o diagnóstico com uma chamada real ao Hermes, um modelo inexistente e falhas de ligação e ausência do evento simuladas.
- [x] Cobertura automatizada do registo, da listagem autorizada, de argumentos inválidos e do acesso a pastas externas ou inexistentes. Cobertura registada no checklist anterior.
- [x] Regressão automatizada de ponta a ponta com pedidos em PT-PT ao Hermes, incluindo a escolha da ferramenta e a resposta a falhas de execução. Cobertura registada no checklist anterior.

### Permissões e privacidade

- [x] Confirmar que uma chamada recusada não produz efeitos.
- [x] Testar a recusa de um caminho fora das pastas autorizadas.
- [x] Verificar que as credenciais ficam ausentes do histórico apresentado ao utilizador.
- [x] Confirmar que um documento que manda enviar dados não desencadeia um envio. O ensaio usou um excerto de texto de um PDF.

### Teste de aceitação da base técnica

> «Que ficheiros tenho na pasta de teste?»

- [x] Confirmar que o Hermes Agent usa o modelo configurado no Ollama e escolhe a ferramenta de listagem com a pasta certa.
- [x] Confirmar que o JARVIS apresenta os ficheiros reais numa resposta em português de Portugal.
- [x] Retirar a permissão à pasta e repetir o pedido. Confirmar que a leitura é recusada e que a recusa fica registada.
- [x] Pedir a listagem de uma pasta fora da raiz autorizada e confirmar a recusa na resposta e nos registos do Hermes.
- [x] Desligar o Ollama e repetir o pedido. Confirmar que o diagnóstico identifica a falha e que o JARVIS comunica o erro.

Validação em 14 de novembro de 2026. O teste de ponta a ponta usou o Hermes com Qwen3, as notas de exemplo e uma política por conta local do gateway. A auditoria confirmou a listagem, as falhas e a recusa após retirar a autorização. A app respondeu a um excerto de PDF que continha uma instrução de envio sem chamar ferramentas. Nesta fase, o conteúdo externo foi fornecido como excerto de texto. O teste de indisponibilidade parou uma instância isolada do Ollama e verificou o erro no diagnóstico e na app.

## Fase 2 — MVP

Usa o [guião detalhado de testes manuais da Fase 2](TESTES_FASE_2.md) para os passos de execução com o portátil. As notas sobre simulações e validações de desenvolvimento mantêm-se como histórico.
O ensaio real dos 45 minutos foi interrompido e continua pendente.

### Voz

- [x] Implementar Alt+Shift+D para iniciar e parar o ditado com o JARVIS em foco. Validado com reconhecimento simulado.
- [ ] Confirmar que o microfone físico fica ativo ao usar Alt+Shift+D.
- [x] Implementar o botão **Ditar** para iniciar e parar a transcrição local em PT-PT e rever o texto antes de enviar. Validado no Chromium com reconhecimento simulado.
- [x] Disponibilizar **Ouvir resposta**, dar preferência a uma voz local PT-PT e expor **Parar leitura** durante a reprodução. Validado com síntese simulada.
- [ ] Confirmar a leitura em voz alta com uma voz portuguesa instalada e a saída de áudio do portátil.
- [ ] Abrir a escuta por botão e confirmar que o utilizador consegue terminá-la pelo mesmo painel.
- [ ] Transcrever pedidos com o microfone do portátil em português de Portugal.
- [ ] Ditar um comando e verificar que a ação correspondente é executada a partir da transcrição.
- [x] Enfileirar frases para leitura automática à medida que o Hermes envia a resposta. Validado com síntese simulada.
- [x] Cancelar a fila de leitura e bloquear a leitura das frases seguintes da resposta em curso. Validado com síntese simulada.
- [ ] Interromper a voz a meio de uma frase e confirmar que o áudio para imediatamente, incluindo o que já estava em fila.
- [x] Reconhecer «cancela» durante um pedido e fechar a ligação ao Hermes. Validado com reconhecimento simulado e um servidor de teste.
- [ ] Confirmar com voz real que «cancela» interrompe um pedido em curso no Hermes.
- [x] Corrigir o último lembrete com «afinal, daqui a 30 minutos» e confirmar que só o aviso corrigido dispara. Validado no Chromium.
- [x] Alterar a voz local e confirmar a mudança na resposta seguinte. Validado com síntese simulada.
- [x] Alterar a velocidade de leitura e confirmar a mudança na resposta seguinte. Validado com síntese simulada.
- [x] Permitir selecionar um microfone e passar a faixa selecionada ao reconhecimento local. Validado no Chromium com um dispositivo simulado.
- [ ] Confirmar a captura com o microfone físico selecionado.
- [ ] Confirmar que a voz é reproduzida na saída selecionada no Windows.

### Conversa

- [x] Manter o contexto entre perguntas sucessivas na mesma sessão. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [x] Resolver referências como «esse ficheiro» e «a reunião de amanhã» quando o contexto identifica uma única opção. Depende da pesquisa de ficheiros ou da consulta da agenda. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [x] Pedir esclarecimento quando duas opções correspondem ao pedido e aguardar a seleção antes de agir. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [x] Alternar o idioma da resposta durante uma conversa quando o utilizador pedir. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [x] Ajustar o nível de detalhe quando o utilizador pedir uma resposta mais curta ou mais completa. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.

### Windows e aplicações

- [x] Abrir aplicações Windows suportadas pelo nome. Validado com lançamento simulado.
- [x] Enviar um ficheiro de texto pelo caminho selecionado ao VS Code. Validado com lançamento simulado.
- [x] Encaminhar um endereço HTTP ou HTTPS para o navegador predefinido. Validado com abertura simulada.
- [x] Alterar o volume do Windows e verificar o nível resultante. Validação prévia registada. Repetir no guião manual.
- [x] Mudar o dispositivo de áudio predefinido do Windows e verificar a seleção no sistema. Validação prévia registada. Repetir no guião manual.

### Programação

- [x] Confirmar a pasta aberta no VS Code e verificar a mensagem quando o editor está indisponível.
- [x] Resolver outros projetos autorizados por nome ou seleção e encaminhar a pasta para o VS Code. Validado com pastas de teste.

### Pesquisa pessoal

- [x] Estender a pesquisa por nome e conteúdo aos restantes projetos autorizados. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [x] Encontrar as notas da última sessão de um projeto autorizado em `notes/AAAA-MM-DD/`, mostrando os ficheiros e a origem da data. Validado no chat com pastas de teste.

### Ficheiros e documentos

- [x] Guardar uma nota e confirmar que o ficheiro contém o texto pedido.

### Agenda e tarefas

- [ ] Consultar a agenda externa ligada e comparar os compromissos com os do dia solicitado no calendário original.
- [x] Consultar a disponibilidade num intervalo e apresentar os períodos livres. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [x] Criar um temporizador e confirmar o disparo com um intervalo de teste no Chromium.
- [x] Criar um lembrete relativo no chat, mostrar a hora calculada e emitir um aviso com a página aberta. Validado no Chromium com um intervalo de teste.
- [x] Editar o último lembrete e confirmar em teste que só o aviso corrigido dispara.
- [x] Cancelar o último lembrete pendente e confirmar em teste que o aviso não dispara.

### Painel e acessibilidade

- [x] Mostrar os estados do microfone no painel. Validado com reconhecimento simulado.
- [x] Confirmar a transcrição parcial durante a escuta. Validado com reconhecimento simulado.
- [x] Mostrar legendas ao início de cada trecho lido e ocultá-las no fim. Validado com síntese simulada.
- [x] Confirmar no pedido em curso que **Cancelar pedido** fecha o fluxo de resposta.
- [x] Permitir usar o chat, a escuta e o botão **Parar** por teclado. Verificado durante o desenvolvimento anterior ao pedido de suspender os testes; repetir no guião manual.
- [ ] Verificar a ordem do foco, os rótulos dos controlos, o contraste e a leitura dos estados com tecnologias de apoio.

### Funcionamento local e desempenho

- [ ] Desligar a Internet após instalar os componentes locais e verificar a conversa, a transcrição, a leitura em voz alta e os comandos básicos do Windows.
- [x] Simular uma integração externa indisponível e verificar que o erro aparece no comando afetado e os comandos locais continuam a funcionar. Validação prévia registada. Repetir no guião manual.

### Teste de aceitação do MVP

> «Jarvis, abre o meu projeto, encontra as notas da última sessão e lembra-me daqui a 45 minutos de fazer uma pausa.»

- [x] Validar por texto o pedido combinado, incluindo os caminhos das notas e o cálculo dos 45 minutos. A abertura do VS Code foi simulada neste teste.
- [ ] Dizer o pedido em voz alta e confirmar que a transcrição mantém as três ações e o intervalo de 45 minutos.
- [ ] Confirmar que abre o projeto correto.
- [ ] Confirmar que encontra as notas certas e indica os ficheiros ou as ligações onde as encontrou.
- [ ] Confirmar que cria um único lembrete para a hora do pedido mais 45 minutos e comunica essa hora.
- [ ] Deixar passar os 45 minutos e confirmar que o aviso de pausa dispara uma única vez.

## Fase 3 — Memória e rotinas

### Memória

- [x] Guardar uma preferência e demonstrar que é aplicada numa conversa posterior.
- [x] Pedir «esquece isto» e confirmar que a memória selecionada deixa de ser recuperada.
- [x] Editar uma memória e confirmar que a próxima consulta usa o valor atualizado.
- [x] Apagar uma memória pelo editor e confirmar que deixa de aparecer na pesquisa e nas respostas.
- [x] Confirmar que cada instância e o histórico no navegador consultam os registos do perfil configurado.

### Pesquisa pessoal

- [x] Pesquisar uma passagem que só existe na imagem de um PDF digitalizado e confirmar a atualização do índice.
- [x] Verificar separadamente a atualização do índice após criar, alterar, mover e apagar um ficheiro.

### Windows e aplicações

- [x] Mover a janela para o monitor indicado e confirmar a sua posição.
- [x] Ativar o modo de foco do Windows e verificar o estado no sistema.
- [x] Confirmar que a ferramenta só consulta a área de transferência quando autorizada.
- [x] Verificar as aplicações, pastas e janelas abertas para os dois espaços de trabalho.

### Ficheiros e documentos

- [x] Renomear um ficheiro numa pasta de teste e confirmar o novo nome.
- [x] Mover um ficheiro, confirmar que está no destino e verificar a recusa de sobrescrita.
- [x] Identificar duplicados por SHA-256 e apresentar os caminhos. Validado com ficheiros de teste.
- [x] Comprimir os ficheiros selecionados e confirmar o conteúdo do arquivo.
- [x] Extrair um arquivo para a pasta escolhida e confirmar os ficheiros extraídos.
- [x] Converter um ficheiro para o formato pedido e verificar que abre no destino.
- [x] Restaurar um ficheiro de teste a partir de uma cópia de segurança e confirmar que é utilizável.

### Agenda e tarefas

- [x] Criar um evento e verificar o título, a data, a hora e o calendário de destino.
- [x] Reagendar um evento e verificar o novo horário no calendário.
- [x] Concluir uma tarefa recorrente e verificar a próxima ocorrência.
- [x] Reagendar um evento com lembrete e confirmar que o aviso acompanha o novo horário.
- [x] Reservar um bloco de foco e verificar que aparece na agenda.
- [x] Configurar a antecedência e confirmar que o aviso dispara no momento definido.

### Rotinas e fluxos

- [x] Criar uma regra e verificar que reage ao evento escolhido.
- [x] Agendar o modo programação e confirmar que arranca à hora configurada com relógio de teste.
- [x] Testar uma rotina condicionada com a condição verdadeira e falsa.

### Funcionamento local e desempenho

- [x] Consultar, editar e recuperar a memória após reiniciar. Validado com ligações limitadas ao próprio computador.

### Extensões e manutenção

- [x] Restaurar uma cópia de teste e verificar as definições, memórias e rotinas recuperadas.

### Validação

- [x] Encontrar uma passagem que só existe na imagem de um PDF, com OCR a pedido e referência à página.
- [x] Criar um ZIP de um ficheiro e extrair uma cópia com conteúdo idêntico. Validar a recusa de um caminho externo dentro do ZIP.
- [x] Copiar um ficheiro de teste e confirmar o conteúdo da cópia.
- [x] Confirmar com uma janela de teste do Windows as operações de minimizar, maximizar, restaurar e mudar de monitor.
- [x] Confirmar com relógio de teste que o aviso acompanha um evento reagendado e só é entregue uma vez.

- [x] Enviar o pedido combinado pela API local e confirmar o registo da memória, a localização da nota de teste e o agendamento para as 09:00.
- [x] Reabrir a base local, avançar o relógio de teste e confirmar que a rotina é executada uma vez, com o VS Code simulado.
- [x] Criar e restaurar uma cópia SQLite de memórias e rotinas num perfil novo. O teste de aceitação inclui também as definições de voz do perfil.
- [x] Validar no Chromium a seleção de uma memória com dados de teste e a pesquisa e reabertura de uma conversa guardada no navegador.

### Teste de aceitação de memória e rotinas

> «Lembra-te de que o meu projeto principal é o JARVIS. Encontra a nota onde escrevi sobre temporizadores e, amanhã às nove, ativa o modo programação.»

- [x] Confirmar que a memória apresenta a informação, a data e a origem.
- [x] Confirmar que a pesquisa encontra a passagem e permite abrir a nota.
- [x] Editar a memória do projeto, reabrir os dados da sessão agendada e confirmar que o valor editado continua disponível no teste automatizado.
- [x] Confirmar que a rotina continua agendada após reabrir os dados, dispara às nove no relógio de teste e pede ao VS Code para abrir o projeto e as notas.
- [x] Validar com relógio real um agendamento curto depois de terminar e voltar a arrancar o servidor. O VS Code abriu a pasta e a nota de teste. O horário das 09:00 foi validado separadamente com relógio de teste.

## Fase 4 — Tarefas em vários passos

### Automatização de aplicações

- [ ] Pedir um ecrã ou recurso e verificar o destino na aplicação integrada.
- [ ] Transferir dados entre dois serviços autorizados e conferir os campos no destino.
- [ ] Abrir o ficheiro gerado por uma sequência e conferir os dados esperados.
- [ ] Executar uma sequência integrada e conferir o resultado de cada ação importante.
- [ ] Executar uma sequência na interface visual e conferir o estado final após cada ação importante.

### Ficheiros e documentos

- [ ] Criar um DOCX, reabri-lo e conferir o conteúdo pedido.
- [ ] Editar parágrafos num DOCX existente e conferir as alterações pedidas.
- [ ] Criar um XLSX e conferir os valores e as fórmulas solicitadas.
- [ ] Editar uma folha existente, reabri-la e conferir as células e os resultados após recalcular numa aplicação de folha de cálculo.
- [ ] Criar uma apresentação e conferir o conteúdo dos diapositivos.
- [ ] Editar uma apresentação existente e conferir os diapositivos alterados.
- [ ] Conferir as linhas e colunas do CSV com a tabela na página de origem.

### Email e mensagens

- [ ] Verificar o acesso às conversas autorizadas em cada serviço ligado.
- [ ] Anexar ficheiros a um rascunho local, conferir nomes e versões e verificar destinatários, assunto, texto e anexos ao abrir o EML. Alterar um ficheiro após a revisão e confirmar que a exportação é recusada até ser revisto de novo.
- [ ] Conferir nomes e versões dos anexos na mensagem do serviço de email antes de autorizar o envio.
- [ ] Cancelar antes de confirmar e verificar no serviço que a mensagem fica por enviar.
- [ ] Gerar um rascunho local a partir da comparação de PDFs, editar o destinatário, o assunto e o conteúdo, e confirmar que o rascunho guardado e a exportação TXT contêm essas alterações.
- [ ] Pesquisar conversas de teste por contacto, assunto e conteúdo. Conferir o resumo, as perguntas por responder, as tarefas e as datas com as mensagens originais. Incluir uma data ambígua e verificar o pedido de esclarecimento.
- [ ] Ditar uma resposta, rever a transcrição, o destinatário e o rascunho, e conferir a referência de envio e a confirmação na pasta de enviados após uma aprovação de teste.

### Reuniões

- [ ] Verificar que a captura só começa após consentimento e termina quando a transcrição é parada.

### Internet e investigação

- [ ] Abrir os resultados selecionados e conferir o conteúdo na fonte original.

### Programação

- [ ] Verificar os limites de acesso ao projeto durante a execução isolada.
- [ ] Pesquisar código e conferir os caminhos e números de linha. Rever uma proposta, aprová-la e conferir a alteração. Modificar o ficheiro após a revisão de outra proposta e verificar que a aprovação é recusada.
- [ ] Conferir o estado, o ramo e o histórico do Git. Comparar as estatísticas apresentadas com as alterações preparadas e por preparar.

### Rotinas e fluxos

- [ ] Confirmar que o fluxo aguarda a aprovação antes de comparar os PDFs.
- [ ] Pedir «avisa-me quando o download acabar», reiniciar o JARVIS enquanto decorre e confirmar que o aviso é emitido uma única vez quando terminar.
- [ ] Reiniciar o JARVIS quando uma tarefa aguarda aprovação e confirmar que retoma nesse ponto.
- [ ] Simular um erro intermédio, repetir o passo em falta e verificar que os passos concluídos permanecem registados.
- [ ] Simular uma falha após o serviço aceitar um envio e confirmar que o JARVIS verifica o estado antes de tentar outra vez.

### Permissões e privacidade

- [ ] Testar que uma conta não autorizada fica inacessível.
- [ ] Testar, para cada ação sujeita a confirmação, os casos de aprovação, recusa e cancelamento.

### Extensões e manutenção

- [ ] Verificar que a ferramenta MCP respeita as permissões registadas.
- [ ] Instalar uma extensão e confirmar que as ferramentas permitidas aparecem no registo.
- [ ] Desativar uma extensão e confirmar que as chamadas às suas ferramentas são recusadas.
- [ ] Simular a falha de uma integração e verificar que o painel identifica o serviço indisponível.

### Estudo e trabalho

- [ ] Consultar o progresso de uma fase de um projeto autorizado e conferir as contagens, os itens pendentes, as linhas e os prazos com o checklist original.

### Conversa

- [ ] Acompanhar no painel os passos planeados, em execução e concluídos. Corrigir a escolha de ficheiros antes da comparação e confirmar que o fluxo usa a seleção revista.

### Vida prática

- [ ] Registar o mesmo artigo em dois locais do inventário, atualizar a quantidade num deles e pesquisar por nome e por local. Reabrir a aplicação e confirmar que os registos persistem no perfil.
- [ ] Catalogar recibos PDF de dois comerciantes em datas distintas. Pesquisar por comerciante e intervalo de datas e abrir o PDF original a partir do resultado.
- [ ] Registar despesas em categorias e datas diferentes, incluindo valores com cêntimos. Conferir os totais por categoria e período e confirmar que uma despesa anulada deixa de contar.

### Teste de aceitação de tarefas em vários passos

> «Encontra o PDF do orçamento, compara-o com a versão anterior e prepara um email com as alterações.»

- [ ] Confirmar que localiza os dois PDFs certos e pede esclarecimento se houver mais de uma versão anterior plausível.
- [ ] Confirmar que apresenta as diferenças e aponta para as páginas correspondentes nas duas versões.
- [ ] Confirmar que o rascunho inclui as alterações e que apresenta o destinatário, o conteúdo e eventuais anexos para revisão.
- [ ] Simular uma falha depois da comparação, reiniciar e confirmar que retoma no passo do rascunho, sem repetir a comparação.
- [ ] Cancelar a primeira tentativa de envio e verificar que não há mensagem enviada.
- [ ] Aprovar um envio de teste, simular uma falha na resposta do serviço e confirmar que o JARVIS verifica o envio antes de repetir a ação. Verificar que existe uma única mensagem enviada.

## Fase 5 — Versão avançada

### Programação

- [ ] Verificar que a extensão mostra exatamente o conteúdo a enviar.

### Voz

- [ ] Dizer «Olá, Jarvis» e verificar que a transcrição começa com indicação de escuta.

### Ecrã, imagens e câmara

- [ ] Confirmar que a captura da janela termina quando a partilha é parada.
- [ ] Confirmar a ativação explícita e verificar que a captura da câmara fica inativa ao terminar.

### Casa inteligente

- [ ] Controlar música pela integração e conferir o estado apresentado com o dispositivo.
- [ ] Mudar o estado de uma luz e conferir o resultado no dispositivo.
- [ ] Mudar o estado de uma tomada e conferir o resultado no dispositivo.
- [ ] Mover um estore e conferir a posição final.
- [ ] Alterar a climatização e conferir a temperatura alvo ou o modo no dispositivo.
- [ ] Enviar um comando ao aspirador e conferir o estado reportado.
- [ ] Ativar uma cena e verificar o estado final de cada dispositivo.
- [ ] Agendar uma cena e confirmar a ativação no momento definido.

### Música e entretenimento

- [ ] Alterar o volume de uma divisão e conferir o nível resultante.
- [ ] Selecionar um episódio e verificar que é o episódio reproduzido.
- [ ] Selecionar um vídeo e conferir o título reproduzido.
- [ ] Adicionar, remover e mover itens e verificar a ordem da fila de reprodução.

### Telemóvel e acesso remoto

- [ ] Suspender uma tarefa remotamente e verificar que nenhuma etapa seguinte arranca.
- [ ] Usar a ação rápida de uma notificação e confirmar que afeta a tarefa certa.
- [ ] Alterar uma tarefa em cada direção e verificar que a alteração aparece no outro dispositivo.
- [ ] Enviar uma fotografia e conferir a pasta de destino.
- [ ] Enviar um documento e verificar que abre no destino.
- [ ] Cancelar remotamente uma tarefa e confirmar o resultado no PC e no telemóvel.

### Conversa

- [ ] Retomar uma conversa no telemóvel e conferir o contexto e o perfil.

### Agenda e tarefas

- [ ] Autorizar a localização, criar um lembrete e verificar que dispara ao chegar ao local configurado.

### Proatividade

- [ ] Agrupar notificações relacionadas e identificar cada evento dentro do grupo.
- [ ] Durante as horas de silêncio, confirmar que avisos sem permissão ficam pendentes.
- [ ] Testar um alerta autorizado a interromper e um sujeito a silêncio.

### Painel e acessibilidade

- [ ] Usar o controlo físico e comparar o efeito com o controlo do painel.

### Permissões e privacidade

- [ ] Testar a recusa de ações pedidas por um telemóvel ou dispositivo doméstico não autorizado.
- [ ] Recusar uma ação física sensível e verificar o estado do dispositivo.
- [ ] Revogar cada permissão e confirmar que a recolha correspondente termina.

### Funcionamento local e desempenho

- [ ] Medir o tempo de resposta a comandos de voz encaminhados para o modelo rápido.
- [ ] Encaminhar uma tarefa longa e verificar se o modelo conclui os passos esperados.
- [ ] Desativar serviços externos e confirmar que os comandos locais continuam disponíveis.

### Teste de aceitação da versão avançada

> «Olá, Jarvis. Mostra-me o que diz o erro na janela ativa, baixa os estores do escritório e avisa-me no telemóvel quando o site do projeto mudar.»

- [ ] Confirmar que a palavra de ativação inicia a escuta e que o JARVIS transcreve o pedido em português de Portugal.
- [ ] Confirmar que lê a mensagem de erro na janela autorizada e encerra a captura após a leitura.
- [ ] Confirmar que atua nos estores do escritório e comunica a posição reportada. Repetir o teste com o dispositivo offline e verificar que apresenta a falha.
- [ ] Alterar uma página de teste e confirmar que o telemóvel recebe um único aviso com a alteração identificada.
- [ ] Repetir durante as horas de silêncio e confirmar que o aviso respeita a regra definida.
- [ ] Cancelar a vigilância no telemóvel e confirmar no PC que a tarefa ficou cancelada.

## Protótipo H.O.L.O Hands

### Validar a base

- [x] Verificar que Python e Ollama estão disponíveis no portátil.
- [x] Iniciar o servidor original do H.O.L.O e confirmar que a API devolve as duas notas de exemplo. Revisão testada: `55626ff`.
- [x] Pedir um resumo em português ao modelo local `qwen3:8b` pelo Ollama.
- [x] Correr o teste integrado em `?probe=1` no Edge (26/26) e abrir uma nota com o rato.
- [ ] Testar os gestos com a webcam física.
- [ ] Executar o Jarvis no Windows e confirmar entrada de microfone e saída de áudio em português.

### Ligar o gesto ao modelo

- [x] Confirmar que a rota local resume uma nota de exemplo e trata uma nota vazia e um modelo em falta.
- [x] Confirmar no Edge que o botão gera e mostra um resumo de uma nota de exemplo.

### Integrar a voz

- [x] Testar a seleção de voz local e a mensagem quando falta uma voz.
- [ ] Ouvir um resumo no portátil com uma voz portuguesa instalada.
- [x] Fazer uma pergunta escrita sobre a nota aberta e confirmar a resposta no Edge.
- [x] Testar transcrição e cancelamento com reconhecimento simulado.
- [ ] Confirmar ditado em português com o microfone físico e um pacote local instalado.
- [ ] Validar a sequência completa com uma nota de exemplo, incluindo a troca de cartão entre pedidos.

### Preparar a instalação

- [ ] Repetir o teste com a Internet desligada depois de descarregar as dependências.
