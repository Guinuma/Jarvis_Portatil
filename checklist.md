# JARVIS Portátil — Checklist de desenvolvimento

Ao concluir uma alteração, atualiza neste ficheiro os itens validados e regista os testes que ainda faltam. Marca uma tarefa quando todos os resultados nela descritos estiverem confirmados.

## Fase 1 — Base técnica

### Funcionamento local e desempenho

- [x] Instalar o Ollama e confirmar que responde a um pedido de teste no portátil.
- [x] Configurar o Hermes Agent para usar o Ollama como fornecedor local e confirmar que um pedido feito na aplicação JARVIS chega ao modelo através do agente.
- [x] Configurar o modelo inicial `qwen3:8b` e confirmar uma chamada real à ferramenta de listagem.
- [x] Escolher e configurar um modelo com suporte a chamadas de ferramentas. Incluir o **Hermes 3** como opção e comparar os candidatos no mesmo portátil quanto à compreensão de português de Portugal, à escolha da ferramenta e ao tempo de resposta.
- [x] Confirmar que o modelo devolve o nome da ferramenta e argumentos válidos, e que o Hermes Agent usa o resultado da execução para responder.
- [x] Testar pedidos em português de Portugal com datas, horas e expressões como «daqui a 45 minutos» e «a reunião de amanhã».
- [x] Medir o tempo até ao início da resposta, o consumo de memória e a taxa de sucesso das chamadas de ferramentas num conjunto fixo de pedidos.

#### Comparação no portátil

Executar `python -m scripts.compare_models qwen3:8b hermes3:3b` com ambos os modelos instalados. Os quatro pedidos usam o Ollama diretamente. As ferramentas de listagem e agenda são apenas esquemas para testar a seleção e os argumentos. A execução real da listagem pelo Hermes Agent foi verificada separadamente.

| Modelo | Hora e data | Chamadas com argumentos corretos | Primeiro texto ou chamada | Memória do modelo no Ollama |
| --- | --- | --- | --- | --- |
| `qwen3:8b` | 2/2 | 1/2 | 1,12–9,78 s | 5,95 GB |
| `hermes3:3b` | 1/2 | 0/2 | 0,40–3,10 s nos três pedidos com saída | 2,57 GB |

Mantém-se o `qwen3:8b` no Hermes Agent. No teste direto, acertou na hora e na data de amanhã, mas usou `autorizada` como caminho em vez de `.` na listagem. O Hermes 3 anunciou suporte a ferramentas, mas não devolveu chamadas estruturadas válidas neste teste. A amostra consiste numa passagem por modelo. Os tempos incluem o estado de carregamento de cada pedido nessa passagem.


### Extensões e manutenção

- [x] Criar um registo de ferramentas com nome, finalidade, argumentos e permissões visíveis para cada ferramenta. A listagem publica o esquema e a indicação de leitura através de MCP.
- [x] Ligar a ferramenta de listagem ao Hermes por MCP e confirmar, através da API local, que o agente a chama e usa o resultado.
- [x] Adicionar um diagnóstico que identifique falhas de ligação ao Ollama e ao Hermes Agent, um modelo em falta e uma ferramenta de listagem indisponível ou não executada. Validado com uma chamada real ao Hermes, um modelo inexistente e falhas de ligação e ausência do evento simuladas.
- [x] Criar testes automatizados do registo, da listagem autorizada, de argumentos inválidos e do acesso a pastas externas ou inexistentes.
- [x] Automatizar a regressão de ponta a ponta com pedidos em PT-PT ao Hermes, incluindo a escolha da ferramenta e a resposta a falhas de execução.

### Permissões e privacidade

- [x] Aplicar permissões por ferramenta e utilizador antes de executar uma chamada. Testar que uma chamada recusada não produz efeitos.
- [x] Restringir ferramentas de ficheiros às pastas autorizadas. Testar um caminho fora dessas pastas.
- [x] Guardar credenciais fora das conversas e verificar que ficam ausentes do histórico apresentado ao utilizador.
- [x] Registar o que o JARVIS executou, porquê e com que resultado, incluindo pedidos recusados e falhas.
- [x] Tratar instruções encontradas em sites, emails e PDFs como conteúdo externo. Testar que um documento que manda enviar dados não desencadeia um envio.

### Teste de aceitação da base técnica

> «Que ficheiros tenho na pasta de teste?»

- [x] Confirmar que o Hermes Agent usa o modelo configurado no Ollama e escolhe a ferramenta de listagem com a pasta certa.
- [x] Confirmar que o JARVIS apresenta os ficheiros reais numa resposta em português de Portugal.
- [x] Retirar a permissão à pasta e repetir o pedido. Confirmar que a leitura é recusada e que a recusa fica registada.
- [x] Pedir a listagem de uma pasta fora da raiz autorizada e confirmar a recusa na resposta e nos registos do Hermes.
- [x] Desligar o Ollama e repetir o pedido. Confirmar que o diagnóstico identifica a falha e que o JARVIS comunica o erro.

Validação em 14 de novembro de 2026. O teste de ponta a ponta usou o Hermes com Qwen3, as notas de exemplo e uma política por conta local do gateway. A auditoria confirmou a listagem, as falhas e a recusa após retirar a autorização. A app respondeu a um excerto de PDF que continha uma instrução de envio sem chamar ferramentas. Nesta fase, o conteúdo externo foi fornecido como excerto de texto. O teste de indisponibilidade parou uma instância isolada do Ollama e verificou o erro no diagnóstico e na app.


## Fase 2 — MVP

### Voz

- [x] Implementar Alt+Shift+D para iniciar e parar o ditado com o JARVIS em foco. Validado com reconhecimento simulado.
- [ ] Confirmar que o microfone físico fica ativo ao usar Alt+Shift+D.
- [x] Implementar o botão **Ditar** para iniciar e parar a transcrição local em PT-PT e rever o texto antes de enviar. Validado no Chromium com reconhecimento simulado.
- [x] Disponibilizar **Ouvir resposta**, dar preferência a uma voz local PT-PT e expor **Parar leitura** durante a reprodução. Validado com síntese simulada.
- [ ] Confirmar a leitura em voz alta com uma voz portuguesa instalada e a saída de áudio do portátil.
- [ ] Abrir a escuta por botão e confirmar que o utilizador consegue terminá-la pelo mesmo painel.
- [ ] Transcrever pedidos com o microfone do portátil em português de Portugal.
- [ ] Executar comandos por voz a partir da transcrição. Depende da transcrição e das ferramentas registadas.
- [x] Enfileirar frases para leitura automática à medida que o Hermes envia a resposta. Validado com síntese simulada.
- [x] Cancelar a fila de leitura e bloquear a leitura das frases seguintes da resposta em curso. Validado com síntese simulada.
- [ ] Interromper a voz a meio de uma frase e confirmar que o áudio para imediatamente, incluindo o que já estava em fila.
- [ ] Reconhecer «cancela» durante uma operação e confirmar que o pedido pendente é cancelado. Depende da transcrição e do cancelamento da operação.
- [ ] Corrigir um pedido com uma instrução como «afinal, daqui a 30 minutos» sem reiniciar a conversa. Confirmar que fica apenas o lembrete corrigido. Depende do contexto e da edição de lembretes.
- [ ] Alterar a voz de leitura e confirmar a mudança na resposta seguinte.
- [ ] Alterar a velocidade da leitura e confirmar a mudança na resposta seguinte.
- [ ] Escolher o microfone e verificar que o áudio é captado pelo dispositivo selecionado.
- [ ] Escolher a saída de áudio e verificar que a resposta é reproduzida no dispositivo selecionado.
- [x] Desativar **Ler respostas automaticamente** e receber a resposta por texto.

### Conversa

- [ ] Manter o contexto entre perguntas sucessivas na mesma sessão.
- [ ] Resolver referências como «esse ficheiro» e «a reunião de amanhã» quando o contexto identifica uma única opção. Depende da pesquisa de ficheiros ou da consulta da agenda.
- [ ] Pedir esclarecimento quando duas opções correspondem ao pedido e aguardar a seleção antes de agir.
- [ ] Alternar o idioma da resposta durante uma conversa quando o utilizador pedir.
- [ ] Ajustar o nível de detalhe quando o utilizador pedir uma resposta mais curta ou mais completa.

### Windows e aplicações

- [ ] Abrir uma aplicação instalada a partir do seu nome.
- [ ] Abrir um ficheiro pelo caminho encontrado ou selecionado.
- [ ] Abrir um site no navegador predefinido.
- [ ] Alterar o volume do Windows e verificar o nível resultante.
- [ ] Mudar o dispositivo de áudio predefinido do Windows e verificar a seleção no sistema.

### Programação

- [ ] Abrir o projeto certo a partir de um nome reconhecido. Pedir a pasta ou a seleção quando houver vários projetos com o mesmo nome.

### Pesquisa pessoal

- [ ] Encontrar ficheiros pelo nome nas pastas autorizadas e apresentar ligações para os abrir.
- [ ] Encontrar ficheiros pelo conteúdo nas pastas autorizadas.
- [ ] Pesquisar notas e identificar as da última sessão de um projeto, mostrando os ficheiros e a origem da data usada para os selecionar.

### Ficheiros e documentos

- [ ] Criar um ficheiro numa pasta autorizada e devolver a sua localização.
- [ ] Guardar uma nota ditada ou escrita e confirmar que pode ser reaberta com o conteúdo pedido.

### Agenda e tarefas

- [ ] Consultar a agenda ligada e devolver os compromissos do dia solicitado.
- [ ] Consultar a disponibilidade num intervalo e apresentar os períodos livres.
- [ ] Criar um temporizador e confirmar que o aviso dispara ao fim do intervalo indicado.
- [ ] Criar um lembrete para uma hora absoluta ou relativa, mostrar a hora calculada e emitir a notificação nessa altura.
- [ ] Editar um lembrete e confirmar que dispara apenas na nova hora.
- [ ] Cancelar um lembrete e confirmar que a notificação deixa de estar agendada.

### Painel e acessibilidade

- [x] Apresentar um chat com entrada por texto e respostas legíveis.
- [x] Abrir o Jarvis normal no navegador com o atalho do Windows.
- [x] Apresentar o início e a conclusão de uma chamada real de ferramenta no painel de atividade do Hermes.
- [x] Abrir o painel H.O.L.O Hands a partir do Jarvis normal quando o submódulo está instalado.
- [ ] Mostrar o estado do microfone enquanto está ativo, inativo ou indisponível.
- [ ] Mostrar a transcrição em direto durante a escuta.
- [ ] Mostrar legendas sincronizadas com as respostas faladas.
- [ ] Mostrar um botão **Parar** visível durante a execução e confirmar que interrompe uma tarefa cancelável.
- [ ] Permitir usar o chat, a escuta e o botão **Parar** por teclado.
- [ ] Verificar a ordem do foco, os rótulos dos controlos, o contraste e a leitura dos estados com tecnologias de apoio.

### Funcionamento local e desempenho

- [ ] Desligar a Internet após instalar os componentes locais e verificar a conversa, a transcrição, a leitura em voz alta e os comandos básicos do Windows.
- [ ] Confirmar que a indisponibilidade de uma integração externa é apresentada no comando que depende dela e que os comandos locais continuam a funcionar.

### Teste de aceitação do MVP

> «Jarvis, abre o meu projeto, encontra as notas da última sessão e lembra-me daqui a 45 minutos de fazer uma pausa.»

- [ ] Dizer o pedido em voz alta e confirmar que a transcrição mantém as três ações e o intervalo de 45 minutos.
- [ ] Confirmar que abre o projeto correto.
- [ ] Confirmar que encontra as notas certas e indica os ficheiros ou as ligações onde as encontrou.
- [ ] Confirmar que cria um único lembrete para a hora do pedido mais 45 minutos e comunica essa hora.
- [ ] Deixar passar os 45 minutos e confirmar que o aviso de pausa dispara uma única vez.

## Fase 3 — Memória e rotinas

### Conversa

- [ ] Guardar o histórico de uma sessão e reabrir a conversa com o contexto anterior após fechar o JARVIS.

### Memória

- [ ] Guardar uma preferência e demonstrar que é aplicada numa conversa posterior.
- [ ] Guardar um contacto e recuperá-lo pelo nome.
- [ ] Guardar um projeto e recuperar a pasta associada.
- [ ] Guardar um nome de dispositivo e resolvê-lo num pedido posterior.
- [ ] Guardar uma rotina com o nome escolhido e recuperá-la por esse nome.
- [ ] Interpretar «lembra-te disto», guardar a informação indicada e mostrá-la no editor.
- [ ] Interpretar «esquece isto» e confirmar que a memória selecionada deixa de ser recuperada.
- [ ] Pesquisar conversas anteriores e abrir a conversa onde aparece o resultado.
- [ ] Identificar nas respostas se uma afirmação veio de uma memória guardada ou de uma dedução.
- [ ] Mostrar a data e a origem de cada memória.
- [ ] Editar uma memória e confirmar que a próxima consulta usa o valor atualizado.
- [ ] Apagar uma memória pelo editor e confirmar que deixa de aparecer na pesquisa e nas respostas.
- [ ] Exportar as memórias num ficheiro legível, com a data e a origem dos registos.
- [ ] Isolar as memórias e o histórico por perfil. Testar que um perfil não consegue consultar os registos de outro.

### Pesquisa pessoal

- [ ] Pesquisar texto em PDFs nas pastas autorizadas.
- [ ] Pesquisar transcrições guardadas nas pastas autorizadas.
- [ ] Indexar o texto de documentos digitalizados por reconhecimento ótico de caracteres e encontrar uma passagem que só exista na imagem.
- [ ] Resumir um documento encontrado e apresentar a ligação para o original.
- [ ] Responder a perguntas com ligações para as fontes e páginas quando aplicável.
- [ ] Atualizar o índice quando um ficheiro é criado, alterado, movido ou apagado. Testar os quatro casos.

### Windows e aplicações

- [ ] Gerir janelas, incluindo mover, minimizar, maximizar e restaurar uma janela identificada.
- [ ] Mover uma janela para o monitor indicado e confirmar a sua posição.
- [ ] Ativar o modo de foco do Windows e verificar o estado.
- [ ] Consultar a bateria e apresentar a percentagem e o estado de carregamento.
- [ ] Consultar o armazenamento e apresentar o espaço disponível na unidade pedida.
- [ ] Fazer uma captura de ecrã e devolver o ficheiro criado.
- [ ] Ler a seleção ativa a pedido e apresentar o texto selecionado.
- [ ] Ler a área de transferência a pedido e confirmar que a ferramenta só a consulta quando autorizada.
- [ ] Criar espaços de trabalho como «modo estudo» e «modo programação» e verificar as aplicações, pastas e janelas abertas para cada um.

### Ficheiros e documentos

- [ ] Renomear um ficheiro e confirmar o novo nome.
- [ ] Mover um ficheiro e confirmar que está no destino.
- [ ] Pré-visualizar uma reorganização de Downloads e aplicar apenas os movimentos aprovados.
- [ ] Identificar duplicados e apresentar os caminhos e o critério usado para os agrupar.
- [ ] Comprimir os ficheiros selecionados e confirmar o conteúdo do arquivo.
- [ ] Extrair um arquivo para a pasta escolhida e confirmar os ficheiros extraídos.
- [ ] Converter um ficheiro para o formato pedido e verificar que abre no formato de destino.
- [ ] Preparar uma cópia de segurança de ficheiros selecionados e restaurar um ficheiro de teste para confirmar que é utilizável.

### Agenda e tarefas

- [ ] Criar um evento e verificar o título, a data, a hora e o calendário de destino.
- [ ] Reagendar um evento e verificar o novo horário no calendário.
- [ ] Detetar conflitos antes de criar ou reagendar um evento e mostrar os compromissos que se sobrepõem.
- [ ] Preparar a agenda do dia por ordem cronológica.
- [ ] Criar uma tarefa recorrente e verificar a próxima ocorrência após concluir a atual.
- [ ] Criar um lembrete associado a um evento e confirmar que acompanha o evento quando este é reagendado.
- [ ] Reservar um bloco de foco e verificar que aparece na agenda.
- [ ] Configurar a antecedência de um aviso de compromisso e confirmar que dispara no momento definido.

### Vida prática

- [ ] Adicionar, remover e marcar como comprados itens numa lista de compras e recuperar a lista na sessão seguinte.

### Rotinas e fluxos

- [ ] Criar uma regra do tipo «quando acontecer X, faz Y» e testar que reage ao evento escolhido.
- [ ] Agendar uma rotina e confirmar que arranca à hora configurada.
- [ ] Adicionar uma condição a uma rotina e testar os casos em que é verdadeira e falsa.
- [ ] Pré-visualizar as etapas, os destinos e os efeitos previstos de uma rotina.
- [ ] Executar uma rotina manualmente a partir do painel, independentemente do horário.
- [ ] Mostrar o histórico da rotina com a hora, os passos executados e o resultado.
- [ ] Configurar «bom dia» para preparar a agenda e mostrar as tarefas do dia.
- [ ] Configurar «modo programação» para ativar o espaço de trabalho escolhido e abrir as notas do projeto.
- [ ] Configurar «fecha o dia» para rever o que ficou pendente e guardar uma nota de fecho.
- [ ] Interpretar «faz como da última vez» e recuperar a rotina correspondente. Pedir esclarecimento se houver duas rotinas plausíveis.

### Painel e acessibilidade

- [ ] Mostrar o histórico de conversas e permitir reabrir uma sessão.
- [ ] Disponibilizar um editor para consultar, editar, apagar e exportar memórias. Depende das operações de memória.
- [ ] Disponibilizar um editor para configurar, pré-visualizar e executar rotinas. Depende do motor de rotinas.

### Funcionamento local e desempenho

- [ ] Confirmar que a memória local pode ser consultada, editada e recuperada depois de reiniciar com a Internet desligada.

### Extensões e manutenção

- [ ] Criar cópias de segurança das definições, memórias e rotinas.
- [ ] Restaurar uma cópia de segurança de teste e verificar que recupera as definições, memórias e rotinas esperadas.

### Teste de aceitação de memória e rotinas

> «Lembra-te de que o meu projeto principal é o JARVIS. Encontra a nota onde escrevi sobre temporizadores e, amanhã às nove, ativa o modo programação.»

- [ ] Confirmar que a memória apresenta a informação, a data e a origem.
- [ ] Confirmar que a pesquisa encontra a passagem e permite abrir a nota.
- [ ] Editar a memória do projeto, reiniciar o JARVIS antes da hora agendada e confirmar que o valor editado continua disponível.
- [ ] Confirmar que a rotina continua agendada após o reinício, dispara às nove e abre o espaço de trabalho configurado.

## Fase 4 — Tarefas em vários passos

### Conversa

- [ ] Mostrar os passos planeados, em execução e concluídos de uma tarefa longa.
- [ ] Permitir que o utilizador intervenha numa tarefa longa para corrigir um ficheiro, destino ou outro parâmetro antes do passo que o utiliza.

### Automatização de aplicações

- [ ] Navegar numa aplicação integrada e verificar que chega ao ecrã ou recurso pedido.
- [ ] Preencher um formulário e mostrar os valores para revisão.
- [ ] Transferir dados entre dois serviços autorizados e conferir os campos no destino.
- [ ] Gerar um ficheiro como resultado de uma sequência e confirmar que abre com os dados esperados.
- [ ] Executar uma sequência de passos pela API ou por um atalho estável, quando disponível, e verificar o resultado de cada ação importante.
- [ ] Usar a interface visual numa aplicação sem integração e confirmar o estado final depois de cada ação importante.
- [ ] Interromper a sequência se um resultado esperado não for confirmado e mostrar o passo que falhou.

### Ficheiros e documentos

- [ ] Criar um documento e reabri-lo para verificar o conteúdo.
- [ ] Editar um documento existente e verificar as alterações pedidas.
- [ ] Criar uma folha de cálculo e verificar os valores e as fórmulas solicitadas.
- [ ] Editar uma folha de cálculo existente e verificar as células e os resultados afetados.
- [ ] Criar uma apresentação e verificar o conteúdo dos diapositivos.
- [ ] Editar uma apresentação existente e verificar os diapositivos alterados.
- [ ] Comparar duas versões de um documento e indicar as diferenças e a respetiva localização.
- [ ] Extrair uma tabela de um PDF e verificar se as linhas e colunas correspondem à origem.

### Pesquisa pessoal

- [ ] Pesquisar emails nas contas autorizadas e ligar os resultados às mensagens originais. Depende da autorização por conta.
- [ ] Localizar as versões pedidas de um documento, compará-las e apresentar as diferenças com referências às duas origens. Depende da pesquisa e da comparação de documentos.

### Email e mensagens

- [ ] Ligar os serviços de email e mensagens usados pelo utilizador e verificar o acesso às conversas autorizadas.
- [ ] Pesquisar uma conversa por contacto, assunto ou conteúdo.
- [ ] Resumir uma conversa e ligar às mensagens que sustentam o resumo.
- [ ] Destacar as perguntas que ainda aguardam resposta.
- [ ] Extrair tarefas mencionadas em mensagens e mostrar as respetivas origens.
- [ ] Extrair datas mencionadas em mensagens e pedir esclarecimento quando forem ambíguas.
- [ ] Redigir uma resposta como rascunho e mostrar o conteúdo para revisão.
- [ ] Selecionar anexos e confirmar os nomes e versões antes do envio.
- [ ] Mostrar destinatários, assunto, conteúdo e anexos antes de pedir confirmação de envio.
- [ ] Enviar a versão confirmada e guardar a referência do envio. Depende da pré-visualização e da confirmação.
- [ ] Responder por voz, permitindo rever a transcrição, o rascunho e o destinatário antes de confirmar. Depende da transcrição e da pré-visualização.
- [ ] Responder a «já enviaste o email?» consultando o estado no serviço ou na pasta de enviados.
- [ ] Cancelar um envio antes da confirmação e verificar que a mensagem fica por enviar.

### Reuniões

- [ ] Preparar notas para uma reunião com ligações para os documentos relevantes.
- [ ] Transcrever uma reunião após obter consentimento e confirmar que a captura termina quando a transcrição é parada.
- [ ] Identificar as decisões tomadas na transcrição.
- [ ] Extrair tarefas da reunião com responsáveis e prazos quando estes forem indicados.
- [ ] Gerar um resumo com marcas temporais que permitem localizar os excertos relevantes.
- [ ] Preparar uma mensagem de seguimento a partir das decisões e tarefas.
- [ ] Associar as notas, a transcrição e o seguimento ao evento ou projeto correto.

### Internet e investigação

- [ ] Pesquisar na web e listar resultados que respondem ao pedido.
- [ ] Abrir as fontes selecionadas e verificar o conteúdo na origem.
- [ ] Comparar resultados de várias fontes e indicar onde concordam ou divergem.
- [ ] Distinguir factos atribuídos a fontes de inferências do JARVIS.
- [ ] Consultar a meteorologia para o lugar e o momento pedidos e mostrar a origem.
- [ ] Consultar o trânsito para o trajeto indicado e mostrar a hora da informação.
- [ ] Consultar horários de transportes para a data e o percurso pedidos.
- [ ] Consultar preços e indicar a moeda, a data e a fonte.
- [ ] Consultar notícias sobre um tema e indicar a data e a fonte.
- [ ] Guardar uma pesquisa com a pergunta, os resultados e as respetivas ligações.
- [ ] Preparar um relatório com ligações para as fontes usadas em cada conclusão.

### Programação

- [ ] Pesquisar código no projeto autorizado e devolver os ficheiros e linhas relevantes.
- [ ] Explicar um erro usando a mensagem e o trecho de código relacionados.
- [ ] Criar as alterações pedidas e mostrar os ficheiros alterados.
- [ ] Correr os testes relevantes e apresentar os resultados, incluindo eventuais falhas.
- [ ] Consultar o estado, o histórico ou o ramo do Git conforme o pedido.
- [ ] Resumir um diff e indicar as alterações principais e os ficheiros afetados.
- [ ] Preparar um pull request com título, descrição e resultados dos testes para revisão.
- [ ] Executar código num ambiente isolado quando necessário e verificar os limites de acesso ao projeto.

### Estudo e trabalho

- [ ] Explicar um tópico com exemplos adequados ao nível pedido.
- [ ] Criar cartões de estudo a partir da matéria indicada.
- [ ] Gerar um teste sobre os tópicos escolhidos.
- [ ] Corrigir respostas e explicar como chegar à solução.
- [ ] Registar os tópicos em que o utilizador teve dificuldades e recuperá-los na sessão seguinte.
- [ ] Gerar um plano de estudo que tenha em conta os tópicos, o tempo disponível e a data de avaliação.
- [ ] Preparar um documento a partir de materiais autorizados e indicar os materiais usados.
- [ ] Acompanhar o progresso de um projeto e mostrar tarefas concluídas, pendentes e próximos prazos.

### Vida prática

- [ ] Sugerir receitas a partir dos ingredientes disponíveis e distinguir os que ainda é preciso comprar.
- [ ] Planear refeições para os dias escolhidos e gerar a lista de ingredientes em falta.
- [ ] Preparar um plano de viagem com as datas, locais e opções de transporte pedidas.
- [ ] Registar itens no inventário doméstico e recuperá-los por nome ou localização.
- [ ] Organizar recibos e permitir encontrá-los por data ou comerciante.
- [ ] Acompanhar despesas e apresentar totais por período e categoria.
- [ ] Preparar um carrinho e mostrar os artigos, as quantidades e o total para aprovação.
- [ ] Preparar uma reserva e mostrar as opções, as datas e as condições para aprovação.
- [ ] Preparar um formulário e mostrar os dados preenchidos para aprovação antes da submissão.

### Rotinas e fluxos

- [ ] Inserir uma etapa de aprovação e verificar que a rotina aguarda a decisão antes de continuar.
- [ ] Guardar o estado das tarefas em curso, incluindo o passo atual, os já concluídos e as aprovações pendentes.
  - [ ] Pedir «avisa-me quando o download acabar», reiniciar o JARVIS enquanto decorre e confirmar que o aviso é emitido uma única vez quando terminar.
  - [ ] Reiniciar o JARVIS quando uma tarefa aguarda aprovação e confirmar que retoma nesse ponto.
- [ ] Repetir apenas o passo em falta após uma falha. Simular um erro intermédio e verificar que os passos concluídos permanecem registados.
- [ ] Evitar repetir ações com efeitos externos. Simular uma falha após o serviço aceitar um envio e confirmar que o JARVIS verifica o estado antes de tentar outra vez.
- [ ] Cancelar uma tarefa entre dois passos e mostrar o que já aconteceu e o que ficou por executar.

### Painel e acessibilidade

- [ ] Mostrar as ações pendentes com os detalhes necessários para aprovar ou recusar cada uma.
- [ ] Mostrar as tarefas em execução, o passo atual e os controlos disponíveis para intervir.

### Permissões e privacidade

- [ ] Aplicar permissões por conta e testar que uma conta não autorizada fica inacessível.
- [ ] Pedir confirmação antes de enviar mensagens. Depende de poder mostrar os destinatários, o conteúdo e os anexos.
- [ ] Pedir confirmação antes de efetuar compras. Depende de poder mostrar o vendedor, os artigos e o total.
- [ ] Pedir confirmação antes de eliminar ficheiros permanentemente. Depende de poder identificar os ficheiros e mostrar o efeito da eliminação.
- [ ] Invalidar a confirmação quando o conteúdo ou destino da ação muda e pedir nova confirmação.
- [ ] Testar, para cada ação sujeita a confirmação, os casos de aprovação, recusa e cancelamento.

### Extensões e manutenção

- [ ] Integrar uma ferramenta por MCP e verificar que respeita as permissões registadas.
- [ ] Instalar uma extensão e confirmar que as ferramentas permitidas aparecem no registo.
- [ ] Desativar uma extensão e confirmar que deixa de ser possível chamar as suas ferramentas.
- [ ] Verificar as ligações às integrações e identificar o serviço indisponível a partir do painel.
- [ ] Recuperar após uma falha do JARVIS, restaurando o estado compatível da tarefa e verificando os efeitos externos já confirmados.

### Teste de aceitação de tarefas em vários passos

> «Encontra o PDF do orçamento, compara-o com a versão anterior e prepara um email com as alterações.»

- [ ] Confirmar que localiza os dois PDFs certos e pede esclarecimento se houver mais de uma versão anterior plausível.
- [ ] Confirmar que apresenta as diferenças e aponta para as páginas correspondentes nas duas versões.
- [ ] Confirmar que o rascunho inclui as alterações e que apresenta o destinatário, o conteúdo e eventuais anexos para revisão.
- [ ] Simular uma falha depois da comparação, reiniciar e confirmar que retoma no passo do rascunho, sem repetir a comparação.
- [ ] Cancelar a primeira tentativa de envio e verificar que não há mensagem enviada.
- [ ] Aprovar um envio de teste, simular uma falha na resposta do serviço e confirmar que o JARVIS verifica o envio antes de repetir a ação. Verificar que existe uma única mensagem enviada.

## Fase 5 — Versão avançada

### Voz

- [ ] Ativar a escuta com «Olá, Jarvis» e verificar que passa a transcrever o pedido. Depende da transcrição e da indicação do estado do microfone.

### Ecrã, imagens e câmara

- [ ] Interpretar uma captura de ecrã fornecida pelo utilizador e explicar o que nela aparece.
- [ ] Interpretar a janela ativa a pedido e identificar a aplicação e o conteúdo visível.
- [ ] Ler uma mensagem de erro no ecrã e reproduzir o texto relevante.
- [ ] Identificar o botão referido pelo utilizador numa captura ou janela.
- [ ] Extrair dados de uma imagem e permitir que sejam revistos.
- [ ] Partilhar uma janela temporariamente para acompanhamento em direto e confirmar que a captura termina quando a partilha é parada.
- [ ] Digitalizar um documento com a câmara após ativação explícita e devolver a imagem ou o texto extraído.
- [ ] Interpretar uma imagem da câmara após ativação explícita e confirmar que a captura fica inativa depois de terminar.

### Internet e investigação

- [ ] Vigiar alterações numa página indicada e mostrar o que mudou desde a última verificação. Depende da pesquisa web e das rotinas agendadas.

### Casa inteligente

- [ ] Ligar o Home Assistant ou os serviços dos dispositivos e apresentar os dispositivos autorizados.
- [ ] Controlar luzes e confirmar o estado final.
- [ ] Controlar tomadas e confirmar o estado final.
- [ ] Controlar estores e confirmar a posição resultante.
- [ ] Ajustar a climatização e confirmar a temperatura alvo ou o modo definido.
- [ ] Controlar a reprodução de música através da integração da casa e confirmar o estado do dispositivo.
- [ ] Controlar o aspirador e confirmar o estado reportado.
- [ ] Consultar os sensores da divisão pedida e mostrar a leitura e a hora.
- [ ] Consultar consumos e apresentar os valores para o dispositivo e o período pedidos.
- [ ] Criar uma cena por divisão e verificar o estado de cada dispositivo após a ativação.
- [ ] Agendar uma cena por hora e confirmar que é ativada no momento definido.
- [ ] Mostrar quando um dispositivo não confirmou a mudança e apresentar o último estado conhecido.

### Música e entretenimento

- [ ] Reproduzir a música encontrada no serviço escolhido.
- [ ] Reproduzir um podcast e confirmar o episódio selecionado.
- [ ] Reproduzir um vídeo e confirmar o título selecionado.
- [ ] Gerir a fila de reprodução e verificar a ordem após adicionar, remover ou mover itens.
- [ ] Consultar e controlar o que está a tocar na divisão indicada.
- [ ] Ajustar o volume da reprodução na divisão escolhida e verificar o nível resultante.
- [ ] Retomar um episódio na posição guardada.
- [ ] Encontrar uma música pela descrição e apresentar as correspondências.
- [ ] Encontrar um filme ou uma série pela descrição e apresentar as correspondências.

### Telemóvel e acesso remoto

- [ ] Enviar pedidos por chat no telemóvel e receber a resposta.
- [ ] Usar voz no telemóvel com transcrição e resposta falada.
- [ ] Receber uma notificação no telemóvel com uma ação rápida e confirmar que a ação é aplicada à tarefa certa.
- [ ] Sincronizar tarefas entre PC e telemóvel e verificar que uma alteração feita num aparece no outro.
- [ ] Enviar uma fotografia do telemóvel para o PC e confirmar a pasta de destino.
- [ ] Enviar um documento do telemóvel para o PC e confirmar que abre no destino.
- [ ] Consultar no telemóvel o estado das automações a correr no PC.
- [ ] Suspender remotamente uma tarefa iniciada noutro dispositivo e verificar que nenhuma etapa seguinte arranca.
- [ ] Cancelar remotamente uma tarefa iniciada noutro dispositivo e confirmar o resultado nos dois dispositivos.

### Conversa

- [ ] Retomar no telemóvel uma conversa começada no PC e verificar que mantém o contexto e o perfil corretos. Depende da sincronização e do histórico.

### Agenda e tarefas

- [ ] Criar um lembrete por localização, após autorizar o acesso à localização, e testar que dispara ao chegar ao local configurado. Depende das notificações no telemóvel.

### Proatividade

- [ ] Entregar um briefing da manhã à hora definida, com a agenda e as tarefas relevantes.
- [ ] Alertar quando surge um conflito na agenda e mostrar os eventos envolvidos.
- [ ] Avisar de um prazo com a antecedência configurada.
- [ ] Alertar quando um serviço monitorizado falha e indicar qual deixou de responder.
- [ ] Notificar o utilizador quando se cumpre uma condição que pediu para vigiar, com uma ligação ou referência ao resultado.
- [ ] Aplicar horas de silêncio e confirmar que os avisos sem permissão para interromper ficam pendentes.
- [ ] Agrupar notificações relacionadas e verificar que os eventos continuam identificáveis no grupo.
- [ ] Configurar que tipos de alerta podem interromper o utilizador e testar um alerta permitido e um sujeito a silêncio.

### Painel e acessibilidade

- [ ] Configurar um controlo físico opcional para iniciar a escuta ou parar uma tarefa e verificar que a ação tem o mesmo efeito que no painel.

### Permissões e privacidade

- [ ] Aplicar permissões por dispositivo e testar que um telemóvel ou dispositivo doméstico não autorizado não consegue executar ações.
- [ ] Atribuir uma permissão própria a ações físicas sensíveis, como abrir uma porta.
- [ ] Mostrar o dispositivo e o efeito pretendido antes de pedir confirmação de uma ação física sensível. Testar a recusa e verificar o estado do dispositivo.
- [ ] Revogar a permissão de partilha da janela, câmara ou localização e confirmar que termina a recolha que dependia dela.

### Funcionamento local e desempenho

- [ ] Encaminhar pedidos simples para um modelo rápido e medir o tempo de resposta a comandos de voz.
- [ ] Encaminhar tarefas longas para um modelo mais capaz e verificar se conclui os passos esperados.
- [ ] Ativar o modelo de visão quando o utilizador pede uma análise de imagem, janela ou câmara.
- [ ] Permitir ativar ou desativar serviços externos e confirmar que os comandos locais continuam disponíveis.

### Teste de aceitação da versão avançada

> «Olá, Jarvis. Mostra-me o que diz o erro na janela ativa, baixa os estores do escritório e avisa-me no telemóvel quando o site do projeto mudar.»

- [ ] Confirmar que a palavra de ativação inicia a escuta e que o JARVIS transcreve o pedido em português de Portugal.
- [ ] Confirmar que lê a mensagem de erro na janela autorizada e encerra a captura após a leitura.
- [ ] Confirmar que atua nos estores do escritório e comunica a posição reportada. Repetir o teste com o dispositivo offline e verificar que apresenta a falha.
- [ ] Alterar uma página de teste e confirmar que o telemóvel recebe um único aviso com a alteração identificada.
- [ ] Repetir durante as horas de silêncio e confirmar que o aviso respeita a regra definida.
- [ ] Cancelar a vigilância no telemóvel e confirmar no PC que a tarefa ficou cancelada.

As 24 áreas da proposta original estão representadas nos subtítulos das cinco fases.
